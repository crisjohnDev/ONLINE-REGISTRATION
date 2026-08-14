import os
import io
import base64

import fitz  # PyMuPDF


# ==========================================================
# HELPERS
# ==========================================================

def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _decode_data_url(data):
    """
    Convert a base64 data URL into raw bytes.

    Example:
        data:image/png;base64,AAAA....
    """

    if not data:
        return None

    if isinstance(data, bytes):
        return data

    if not isinstance(data, str):
        return None

    try:
        if "," in data:
            data = data.split(",", 1)[1]

        return base64.b64decode(data)

    except Exception as error:
        print(
            "Base64 decode error:",
            repr(error)
        )
        return None


def _get_page_number(element):
    """
    JavaScript stores page numbers as 1, 2, 3...

    PyMuPDF uses 0, 1, 2...

    Therefore we convert here.
    """

    page = element.get(
        "page",
        element.get(
            "pageIndex",
            1
        )
    )

    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    # JS page numbering is 1-based
    page_index = page - 1

    return page_index


def _get_element_value(element):
    """
    Your JavaScript stores text/date/check/signature
    data in `value`.

    Support multiple possible names for compatibility.
    """

    return (
        element.get("value")
        or element.get("text")
        or element.get("image")
        or element.get("src")
        or element.get("data")
        or ""
    )


# ==========================================================
# MAIN PDF GENERATOR
# ==========================================================

def generate_filled_pdf(
    original_pdf,
    elements,
    output_path
):
    """
    Flatten PDF editor elements onto the original PDF.

    Coordinates coming from the browser are converted from
    the displayed PDF size into the original PDF's native size.

    Supported elements:

        text
        check
        cross
        date
        signature
    """

    print("==========================================")
    print("generate_filled_pdf()")
    print("Source:", original_pdf)
    print("Output:", output_path)
    print("Elements:", len(elements))
    print("==========================================")

    # ======================================================
    # CHECK SOURCE
    # ======================================================

    if not original_pdf:
        raise FileNotFoundError(
            "No original PDF path was supplied."
        )

    if not os.path.exists(original_pdf):
        raise FileNotFoundError(
            f"Original PDF not found: {original_pdf}"
        )

    # ======================================================
    # OPEN PDF
    # ======================================================

    pdf = fitz.open(original_pdf)

    try:

        print(
            "PDF pages:",
            len(pdf)
        )

        # ==================================================
        # PROCESS ELEMENTS
        # ==================================================

        for index, element in enumerate(elements):

            print("==========================================")
            print(
                f"PROCESSING ELEMENT {index + 1}"
            )
            print(
                "Raw element:",
                element
            )

            if not isinstance(element, dict):

                print(
                    "Skipping invalid element."
                )

                continue

            # ==================================================
            # TYPE
            # ==================================================

            element_type = str(
                element.get(
                    "type",
                    ""
                )
            ).strip().lower()

            print(
                "Element type:",
                element_type
            )

            if not element_type:

                print(
                    "Element has no type. Skipping."
                )

                continue

            # ==================================================
            # PAGE
            # ==================================================

            page_index = _get_page_number(
                element
            )

            print(
                "PDF page index:",
                page_index
            )

            if (
                page_index < 0
                or page_index >= len(pdf)
            ):

                print(
                    "Invalid page index:",
                    page_index
                )

                continue

            page = pdf[
                page_index
            ]

            # ==================================================
            # ORIGINAL PDF DIMENSIONS
            # ==================================================

            pdf_width = float(
                page.rect.width
            )

            pdf_height = float(
                page.rect.height
            )

            print(
                "Original PDF size:",
                pdf_width,
                "x",
                pdf_height
            )

            # ==================================================
            # DISPLAY SCALE
            # ==================================================

            display_scale = _to_float(
                element.get(
                    "scale",
                    1
                ),
                1
            )

            if display_scale <= 0:
                display_scale = 1

            print(
                "Display scale:",
                display_scale
            )

            # ==================================================
            # SCREEN COORDINATES
            # ==================================================

            screen_x = _to_float(
                element.get(
                    "x",
                    0
                )
            )

            screen_y = _to_float(
                element.get(
                    "y",
                    0
                )
            )

            screen_width = _to_float(
                element.get(
                    "width",
                    100
                ),
                100
            )

            screen_height = _to_float(
                element.get(
                    "height",
                    30
                ),
                30
            )

            print(
                "Screen coordinates:",
                screen_x,
                screen_y
            )

            print(
                "Screen dimensions:",
                screen_width,
                screen_height
            )

            # ==================================================
            # CONVERT SCREEN → PDF
            #
            # JS renders the PDF using:
            #
            # viewport = original size * scale
            #
            # Therefore:
            #
            # PDF coordinate = screen coordinate / scale
            # ==================================================

            x = (
                screen_x /
                display_scale
            )

            y = (
                screen_y /
                display_scale
            )

            width = (
                screen_width /
                display_scale
            )

            height = (
                screen_height /
                display_scale
            )

            print(
                "Converted PDF coordinates:",
                x,
                y
            )

            print(
                "Converted PDF dimensions:",
                width,
                height
            )

            # ==================================================
            # SAFETY
            # ==================================================

            if width <= 0:
                width = 100

            if height <= 0:
                height = 30

            # Don't allow completely outside page

            if x > pdf_width:
                print(
                    "Element is outside right side."
                )
                continue

            if y > pdf_height:
                print(
                    "Element is outside bottom."
                )
                continue

            # ==================================================
            # TEXT
            # ==================================================

            if element_type == "text":

                text = str(
                    _get_element_value(
                        element
                    )
                ).strip()

                if not text:

                    print(
                        "Text is empty. Skipping."
                    )

                    continue

                # ------------------------------------------------
                # FONT SIZE
                # ------------------------------------------------

                font_size = _to_float(
                    element.get(
                        "fontSize",
                        14
                    ),
                    14
                )

                if font_size <= 0:
                    font_size = 14

                # Convert browser font size to PDF size
                font_size = (
                    font_size /
                    display_scale
                )

                font_size = max(
                    5,
                    min(
                        font_size,
                        72
                    )
                )

                # ------------------------------------------------
                # INSERT TEXT
                # ------------------------------------------------
                #
                # Browser coordinates use TOP-LEFT.
                #
                # PyMuPDF insert_text uses the BASELINE.
                #
                # So add font size to Y.
                # ------------------------------------------------

                insert_x = x

                insert_y = (
                    y +
                    font_size
                )

                print(
                    "Inserting text:",
                    repr(text)
                )

                print(
                    "Text position:",
                    insert_x,
                    insert_y
                )

                page.insert_text(
                    (
                        insert_x,
                        insert_y
                    ),
                    text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(
                        0,
                        0,
                        0
                    ),
                    overlay=True
                )

                print(
                    "TEXT INSERTED SUCCESSFULLY"
                )

            # ==================================================
            # CHECK
            # ==================================================

            elif element_type == "check":

                check_size = max(
                    10,
                    min(
                        width,
                        height
                    )
                )

                check_font_size = (
                    check_size * 1.2
                )

                print(
                    "Inserting checkmark."
                )

                page.insert_text(
                    (
                        x,
                        y + check_font_size
                    ),
                    "✓",
                    fontsize=check_font_size,
                    fontname="helv",
                    color=(
                        0,
                        0,
                        0
                    ),
                    overlay=True
                )

                print(
                    "CHECK INSERTED SUCCESSFULLY"
                )

            # ==================================================
            # CROSS
            # ==================================================

            elif element_type in (
                "cross",
                "x"
            ):

                cross_size = max(
                    10,
                    min(
                        width,
                        height
                    )
                )

                cross_font_size = (
                    cross_size * 1.2
                )

                print(
                    "Inserting X."
                )

                page.insert_text(
                    (
                        x,
                        y + cross_font_size
                    ),
                    "X",
                    fontsize=cross_font_size,
                    fontname="helv",
                    color=(
                        0,
                        0,
                        0
                    ),
                    overlay=True
                )

                print(
                    "CROSS INSERTED SUCCESSFULLY"
                )

            # ==================================================
            # DATE
            # ==================================================

            elif element_type == "date":

                date_text = str(
                    _get_element_value(
                        element
                    )
                ).strip()

                if not date_text:

                    print(
                        "Date is empty. Skipping."
                    )

                    continue

                font_size = _to_float(
                    element.get(
                        "fontSize",
                        12
                    ),
                    12
                )

                font_size = (
                    font_size /
                    display_scale
                )

                font_size = max(
                    5,
                    min(
                        font_size,
                        72
                    )
                )

                print(
                    "Inserting date:",
                    date_text
                )

                page.insert_text(
                    (
                        x,
                        y + font_size
                    ),
                    date_text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(
                        0,
                        0,
                        0
                    ),
                    overlay=True
                )

                print(
                    "DATE INSERTED SUCCESSFULLY"
                )

            # ==================================================
            # SIGNATURE
            # ==================================================

            elif element_type == "signature":

                image_data = _get_element_value(
                    element
                )

                if not image_data:

                    print(
                        "Signature has no image data."
                    )

                    continue

                print(
                    "Signature data received."
                )

                # ------------------------------------------------
                # DECODE IMAGE
                # ------------------------------------------------

                image_bytes = _decode_data_url(
                    image_data
                )

                if not image_bytes:

                    print(
                        "Unable to decode signature."
                    )

                    continue

                print(
                    "Signature bytes:",
                    len(image_bytes)
                )

                # ------------------------------------------------
                # IMAGE RECTANGLE
                # ------------------------------------------------

                rect = fitz.Rect(
                    x,
                    y,
                    x + width,
                    y + height
                )

                print(
                    "Signature rectangle:",
                    rect
                )

                # ------------------------------------------------
                # INSERT IMAGE
                # ------------------------------------------------

                page.insert_image(
                    rect,
                    stream=image_bytes,
                    keep_proportion=True,
                    overlay=True
                )

                print(
                    "SIGNATURE INSERTED SUCCESSFULLY"
                )

            # ==================================================
            # UNKNOWN
            # ==================================================

            else:

                print(
                    "UNKNOWN ELEMENT TYPE:",
                    element_type
                )

        # ======================================================
        # CREATE OUTPUT DIRECTORY
        # ======================================================

        output_directory = os.path.dirname(
            output_path
        )

        if output_directory:

            os.makedirs(
                output_directory,
                exist_ok=True
            )

        # ======================================================
        # REMOVE EXISTING OUTPUT
        # ======================================================

        if os.path.exists(
            output_path
        ):

            try:

                os.remove(
                    output_path
                )

            except OSError as error:

                print(
                    "Unable to remove existing output:",
                    repr(error)
                )

        # ======================================================
        # SAVE
        # ======================================================

        print("==========================================")
        print("SAVING COMPLETED PDF")
        print(
            "Output:",
            output_path
        )
        print("==========================================")

        pdf.save(
            output_path,
            garbage=4,
            deflate=True
        )

        # ======================================================
        # VERIFY
        # ======================================================

        if not os.path.exists(
            output_path
        ):

            raise OSError(
                "PDF output was not created."
            )

        output_size = os.path.getsize(
            output_path
        )

        if output_size <= 0:

            raise OSError(
                "Generated PDF is empty."
            )

        print("==========================================")
        print("PDF GENERATION COMPLETE")
        print(
            "Output:",
            output_path
        )
        print(
            "Size:",
            output_size,
            "bytes"
        )
        print("==========================================")

    finally:

        pdf.close()