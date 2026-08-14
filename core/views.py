from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.utils import create_default_admin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .pdf_editor import generate_filled_pdf
import json
import os
from django.contrib.staticfiles import finders
from django.conf import settings
from django.core.files import File
from django.db import IntegrityError, transaction
from django.core.files import File
import base64
import tempfile
import shutil
from residents.models import Residents


# Create your views here.
def home(request):
    return render(request, 'home.html')

def new_registration(request):

    print("==========================================")
    print("new_registration CALLED")
    print("METHOD:", request.method)
    print("==========================================")

    # ==========================================================
    # GET
    # ==========================================================

    if request.method == "GET":

        return render(
            request,
            "pages/new-registration.html"
        )

    # ==========================================================
    # POST
    # ==========================================================

    if request.method != "POST":

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # FULL NAME
    # ==========================================================

    full_name = " ".join(
        request.POST.get(
            "full_name",
            ""
        )
        .strip()
        .split()
    )

    # ==========================================================
    # CONTACT NUMBER
    # ==========================================================

    contact_number = request.POST.get(
        "contact_number",
        ""
    ).strip()

    # ==========================================================
    # SUPPORTING DOCUMENTS
    # ==========================================================

    supporting_documents = request.FILES.getlist(
        "supporting_document"
    )

    supporting_document = (
        supporting_documents[0]
        if supporting_documents
        else None
    )

    # ==========================================================
    # AGREEMENT
    # ==========================================================

    agreement = request.POST.get(
        "agreement"
    )

    # ==========================================================
    # PDF ELEMENTS
    # ==========================================================

    pdf_elements_json = request.POST.get(
        "pdf_elements",
        "[]"
    )

    try:

        pdf_elements = json.loads(
            pdf_elements_json
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        pdf_elements = []

    if not isinstance(
        pdf_elements,
        list
    ):

        pdf_elements = []

    # ==========================================================
    # DEBUG
    # ==========================================================

    print("==========================================")
    print("NEW REGISTRATION POST")
    print("Full Name:", full_name)
    print("Contact:", contact_number)

    print(
        "Supporting Documents:",
        len(supporting_documents)
    )

    for uploaded_file in supporting_documents:

        print(
            " -",
            uploaded_file.name,
            f"({uploaded_file.size} bytes)"
        )

    print(
        "PDF Elements:",
        len(pdf_elements)
    )

    print(
        "Agreement:",
        bool(agreement)
    )

    # Print every PDF element
    for index, element in enumerate(pdf_elements):

        print(
            f"PDF ELEMENT {index + 1}:",
            element
        )

    print("==========================================")

    # ==========================================================
    # VALIDATE FULL NAME
    # ==========================================================

    if not full_name:

        messages.error(
            request,
            "Full name is required."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # VALIDATE CONTACT
    # ==========================================================

    if not contact_number:

        messages.error(
            request,
            "Contact number is required."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # VALIDATE SUPPORTING DOCUMENT
    # ==========================================================

    if not supporting_document:

        messages.error(
            request,
            "Please upload your supporting document."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # VALIDATE AGREEMENT
    # ==========================================================

    if not agreement:

        messages.error(
            request,
            "You must agree to the certification and data "
            "privacy statement."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # FILE SIZE
    # ==========================================================

    MAX_FILE_SIZE = 10 * 1024 * 1024

    total_file_size = sum(
        uploaded_file.size
        for uploaded_file in supporting_documents
    )

    if total_file_size > MAX_FILE_SIZE:

        messages.error(
            request,
            "The total size of your supporting documents "
            "must not exceed 10MB."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # CHECK EXISTING APPLICATION
    # ==========================================================

    existing = Residents.objects.filter(
        full_name__iexact=full_name
    ).first()

    if existing:

        if existing.status == Residents.Status.PENDING:

            messages.error(
                request,
                "You already have a pending application."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.PRE_APPROVED:

            messages.error(
                request,
                "Your application is already pre-approved."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.APPROVED:

            messages.error(
                request,
                "You are already registered as a voter."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.DUPLICATION:

            messages.error(
                request,
                "Your record already exists as a duplicate."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.REJECTED:

            print(
                "Existing application is REJECTED."
            )

            print(
                "Applicant may submit again."
            )

    # ==========================================================
    # CEF-1 PDF
    #
    # IMPORTANT:
    #
    # Your PDF is located at:
    #
    # web/
    #   core/
    #       static/
    #           docs/
    #               com_res_11177_annexA.pdf
    #
    # Therefore we MUST use:
    #
    # BASE_DIR / core / static / docs
    # ==========================================================

    cef1_pdf = os.path.join(
        settings.BASE_DIR,
        "core",
        "static",
        "docs",
        "com_res_11177_annexA.pdf"
    )

    print("==========================================")
    print("CEF-1 PDF LOCATION")
    print("BASE_DIR:", settings.BASE_DIR)
    print("CEF-1 PDF:", cef1_pdf)
    print(
        "PDF exists:",
        os.path.exists(cef1_pdf)
    )
    print("==========================================")

    # ==========================================================
    # CHECK PDF
    # ==========================================================

    if not os.path.isfile(
        cef1_pdf
    ):

        print(
            "CEF-1 PDF NOT FOUND:"
        )

        print(
            cef1_pdf
        )

        messages.error(
            request,
            "The official CEF-1 application form "
            "could not be found. Please contact the administrator."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # SAFE FILE NAME
    # ==========================================================

    safe_name = "".join(
        character
        for character in full_name
        if (
            character.isalnum()
            or character in (
                " ",
                "-",
                "_"
            )
        )
    ).strip()

    safe_name = "_".join(
        safe_name.split()
    )

    if not safe_name:

        safe_name = "resident"

    # ==========================================================
    # DIRECTORIES
    # ==========================================================

    completed_directory = os.path.join(
        settings.MEDIA_ROOT,
        "completed_applications"
    )

    os.makedirs(
        completed_directory,
        exist_ok=True
    )

    # ==========================================================
    # OUTPUT PDF
    # ==========================================================

    completed_pdf = os.path.join(
        completed_directory,
        f"{safe_name}_CEF-1.pdf"
    )

    # ==========================================================
    # USE TEMP DIRECTORY
    #
    # NamedTemporaryFile on Windows can cause:
    #
    # OSError: [Errno 22] Invalid argument
    #
    # So we create a normal temporary filename and close it
    # before PyMuPDF/reportlab accesses it.
    # ==========================================================

    temp_directory = os.path.join(
        settings.MEDIA_ROOT,
        "temp_pdf"
    )

    os.makedirs(
        temp_directory,
        exist_ok=True
    )

    temp_original = os.path.join(
        temp_directory,
        f"{safe_name}_cef1_source.pdf"
    )

    # ==========================================================
    # REMOVE OLD TEMP FILE
    # ==========================================================

    try:

        if os.path.exists(
            temp_original
        ):

            os.remove(
                temp_original
            )

    except OSError:

        pass

    # ==========================================================
    # PROCESS
    # ==========================================================

    try:

        # ======================================================
        # COPY ORIGINAL PDF
        # ======================================================

        print(
            "Copying original CEF-1 PDF..."
        )

        with open(
            cef1_pdf,
            "rb"
        ) as source:

            with open(
                temp_original,
                "wb"
            ) as destination:

                while True:

                    chunk = source.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    destination.write(
                        chunk
                    )

        print(
            "Source PDF copied successfully."
        )

        print(
            "Temporary source:",
            temp_original
        )

        # ======================================================
        # GENERATE FILLED PDF
        # ======================================================

        print("==========================================")
        print("GENERATING FILLED CEF-1 PDF")
        print(
            "Elements received:",
            len(pdf_elements)
        )
        print("==========================================")

        generate_filled_pdf(
            original_pdf=temp_original,
            elements=pdf_elements,
            output_path=completed_pdf
        )

        # ======================================================
        # VERIFY OUTPUT
        # ======================================================

        if not os.path.exists(
            completed_pdf
        ):

            raise Exception(
                "Completed PDF was not generated."
            )

        output_size = os.path.getsize(
            completed_pdf
        )

        print(
            "Completed PDF:",
            completed_pdf
        )

        print(
            "Completed PDF size:",
            output_size
        )

        if output_size <= 0:

            raise Exception(
                "Completed PDF is empty."
            )

        # ======================================================
        # DATABASE
        # ======================================================

        with transaction.atomic():

            # ==================================================
            # CREATE RESIDENT
            # ==================================================

            resident = Residents.objects.create(

                full_name=full_name,

                contact_number=contact_number,

                document_type=
                    Residents.DocumentType.NEW_REGISTRATION,

                status=
                    Residents.Status.PENDING,

                supporting_document=
                    supporting_document
            )

            # ==================================================
            # SAVE COMPLETED PDF
            # ==================================================

            with open(
                completed_pdf,
                "rb"
            ) as pdf_file:

                resident.document.save(

                    os.path.basename(
                        completed_pdf
                    ),

                    File(
                        pdf_file
                    ),

                    save=True
                )

        # ======================================================
        # SUCCESS
        # ======================================================

        print("==========================================")
        print("REGISTRATION SUCCESS")
        print("==========================================")

        print(
            "Resident ID:",
            resident.id
        )

        print(
            "Tracking Number:",
            resident.tracking_number
        )

        print(
            "Name:",
            resident.full_name
        )

        print(
            "Document:",
            resident.document.name
        )

        if resident.supporting_document:

            print(
                "Supporting Document:",
                resident.supporting_document.name
            )

        print(
            "Status:",
            resident.status
        )

        print("==========================================")

        # ======================================================
        # CLEAN TEMP SOURCE
        # ======================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError as cleanup_error:

            print(
                "Temp cleanup error:",
                cleanup_error
            )

        # ======================================================
        # SUCCESS MESSAGE
        # ======================================================

        messages.success(
            request,
            "Your registration application was submitted successfully."
        )

        # ======================================================
        # SUCCESS PAGE
        # ======================================================

        return redirect(
            "success",
            resident.id
        )

    # ==========================================================
    # DATABASE ERROR
    # ==========================================================

    except IntegrityError as error:

        print("==========================================")
        print("DATABASE INTEGRITY ERROR")
        print("==========================================")

        print(
            "Error:",
            repr(error)
        )

        # ======================================================
        # CLEAN TEMP
        # ======================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:
            pass

        messages.error(
            request,
            "An active application already exists for this resident."
        )

        return redirect(
            "new-registration"
        )

    # ==========================================================
    # OTHER ERROR
    # ==========================================================

    except Exception as error:

        print("==========================================")
        print("NEW REGISTRATION ERROR")
        print("==========================================")

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            repr(error)
        )

        print("==========================================")

        # ======================================================
        # CLEAN TEMP
        # ======================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:
            pass

        # ======================================================
        # CLEAN OUTPUT
        # ======================================================

        try:

            if os.path.exists(
                completed_pdf
            ):

                os.remove(
                    completed_pdf
                )

        except OSError:
            pass

        messages.error(
            request,
            "Unable to process your application. "
            "Please try again."
        )

        return redirect(
            "new-registration"
        )

def transfer(request):

    print("==========================================")
    print("TRANSFER CALLED")
    print("METHOD:", request.method)
    print("==========================================")

    # ==========================================================
    # GET
    # ==========================================================

    if request.method == "GET":

        return render(
            request,
            "pages/transfer.html"
        )

    # ==========================================================
    # POST
    # ==========================================================

    if request.method != "POST":

        return redirect(
            "transfer"
        )

    # ==========================================================
    # FULL NAME
    # ==========================================================

    full_name = " ".join(
        request.POST.get(
            "full_name",
            ""
        )
        .strip()
        .split()
    )

    # ==========================================================
    # CONTACT NUMBER
    # ==========================================================

    contact_number = request.POST.get(
        "contact_number",
        ""
    ).strip()

    # ==========================================================
    # SUPPORTING DOCUMENTS
    # ==========================================================

    supporting_documents = request.FILES.getlist(
        "supporting_document"
    )

    supporting_document = (
        supporting_documents[0]
        if supporting_documents
        else None
    )

    # ==========================================================
    # AGREEMENT
    # ==========================================================

    agreement = request.POST.get(
        "agreement"
    )

    # ==========================================================
    # PDF ELEMENTS
    # ==========================================================

    pdf_elements_json = request.POST.get(
        "pdf_elements",
        "[]"
    )

    try:

        pdf_elements = json.loads(
            pdf_elements_json
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        pdf_elements = []

    if not isinstance(
        pdf_elements,
        list
    ):

        pdf_elements = []

    # ==========================================================
    # DEBUG
    # ==========================================================

    print("==========================================")
    print("TRANSFER POST")
    print("Full Name:", full_name)
    print("Contact:", contact_number)

    print(
        "Supporting Documents:",
        len(supporting_documents)
    )

    for uploaded_file in supporting_documents:

        print(
            " -",
            uploaded_file.name,
            f"({uploaded_file.size} bytes)"
        )

    print(
        "PDF Elements:",
        len(pdf_elements)
    )

    print(
        "Agreement:",
        bool(agreement)
    )

    for index, element in enumerate(pdf_elements):

        print(
            f"PDF ELEMENT {index + 1}:",
            element
        )

    print("==========================================")

    # ==========================================================
    # VALIDATE FULL NAME
    # ==========================================================

    if not full_name:

        messages.error(
            request,
            "Full name is required."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # VALIDATE CONTACT
    # ==========================================================

    if not contact_number:

        messages.error(
            request,
            "Contact number is required."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # VALIDATE SUPPORTING DOCUMENT
    # ==========================================================

    if not supporting_document:

        messages.error(
            request,
            "Please upload your supporting document."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # VALIDATE AGREEMENT
    # ==========================================================

    if not agreement:

        messages.error(
            request,
            "You must agree to the certification and data "
            "privacy statement."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # FILE SIZE
    # ==========================================================

    MAX_FILE_SIZE = 10 * 1024 * 1024

    total_file_size = sum(
        uploaded_file.size
        for uploaded_file in supporting_documents
    )

    if total_file_size > MAX_FILE_SIZE:

        messages.error(
            request,
            "The total size of your supporting documents "
            "must not exceed 10MB."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # CHECK EXISTING TRANSFER APPLICATION
    # ==========================================================

    existing = Residents.objects.filter(
        full_name__iexact=full_name,
        document_type=Residents.DocumentType.TRANSFER
    ).first()

    if existing:

        if existing.status == Residents.Status.PENDING:

            messages.error(
                request,
                "You already have a pending Transfer application."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.PRE_APPROVED:

            messages.error(
                request,
                "Your Transfer application is already pre-approved."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.APPROVED:

            messages.error(
                request,
                "Your Transfer application has already been approved."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.DUPLICATION:

            messages.error(
                request,
                "Your Transfer application was marked as a duplicate."
            )

            return redirect(
                "already_registered",
                existing.id
            )

        elif existing.status == Residents.Status.REJECTED:

            print(
                "Existing Transfer application is REJECTED."
            )

            print(
                "Applicant may submit again."
            )

    # ==========================================================
    # CEF-1 TRANSFER PDF
    # ==========================================================

    cef1_pdf = os.path.join(
        settings.BASE_DIR,
        "core",
        "static",
        "docs",
        "com_res_11177_annexC.pdf"
    )

    print("==========================================")
    print("TRANSFER CEF-1 PDF LOCATION")
    print("BASE_DIR:", settings.BASE_DIR)
    print("CEF-1 PDF:", cef1_pdf)
    print(
        "PDF exists:",
        os.path.exists(cef1_pdf)
    )
    print("==========================================")

    # ==========================================================
    # CHECK PDF
    # ==========================================================

    if not os.path.isfile(
        cef1_pdf
    ):

        messages.error(
            request,
            "The official CEF-1 Transfer application form "
            "could not be found. Please contact the administrator."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # SAFE FILE NAME
    # ==========================================================

    safe_name = "".join(
        character
        for character in full_name
        if (
            character.isalnum()
            or character in (
                " ",
                "-",
                "_"
            )
        )
    ).strip()

    safe_name = "_".join(
        safe_name.split()
    )

    if not safe_name:

        safe_name = "resident"

    # ==========================================================
    # DIRECTORIES
    # ==========================================================

    completed_directory = os.path.join(
        settings.MEDIA_ROOT,
        "completed_transfers"
    )

    os.makedirs(
        completed_directory,
        exist_ok=True
    )

    # ==========================================================
    # OUTPUT PDF
    # ==========================================================

    completed_pdf = os.path.join(
        completed_directory,
        f"{safe_name}_TRANSFER_CEF-1.pdf"
    )

    # ==========================================================
    # TEMP DIRECTORY
    # ==========================================================

    temp_directory = os.path.join(
        settings.MEDIA_ROOT,
        "temp_pdf"
    )

    os.makedirs(
        temp_directory,
        exist_ok=True
    )

    temp_original = os.path.join(
        temp_directory,
        f"{safe_name}_transfer_source.pdf"
    )

    # ==========================================================
    # REMOVE OLD TEMP
    # ==========================================================

    try:

        if os.path.exists(
            temp_original
        ):

            os.remove(
                temp_original
            )

    except OSError:

        pass

    # ==========================================================
    # PROCESS
    # ==========================================================

    try:

        # ======================================================
        # COPY ORIGINAL PDF
        # ======================================================

        print(
            "Copying original Transfer CEF-1 PDF..."
        )

        with open(
            cef1_pdf,
            "rb"
        ) as source:

            with open(
                temp_original,
                "wb"
            ) as destination:

                while True:

                    chunk = source.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    destination.write(
                        chunk
                    )

        print(
            "Source PDF copied successfully."
        )

        # ======================================================
        # GENERATE FILLED PDF
        # ======================================================

        print("==========================================")
        print("GENERATING FILLED TRANSFER CEF-1 PDF")
        print(
            "Elements received:",
            len(pdf_elements)
        )
        print("==========================================")

        # IMPORTANT:
        # Use the SAME argument names as new_registration()

        generate_filled_pdf(
            original_pdf=temp_original,
            elements=pdf_elements,
            output_path=completed_pdf
        )

        # ======================================================
        # VERIFY OUTPUT
        # ======================================================

        if not os.path.exists(
            completed_pdf
        ):

            raise Exception(
                "Completed Transfer PDF was not generated."
            )

        output_size = os.path.getsize(
            completed_pdf
        )

        print(
            "Completed Transfer PDF:",
            completed_pdf
        )

        print(
            "Completed PDF size:",
            output_size
        )

        if output_size <= 0:

            raise Exception(
                "Completed Transfer PDF is empty."
            )

        # ======================================================
        # DATABASE
        # ======================================================

        with transaction.atomic():

            # ==================================================
            # CREATE RESIDENT
            # ==================================================

            resident = Residents.objects.create(

                full_name=full_name,

                contact_number=contact_number,

                document_type=
                    Residents.DocumentType.TRANSFER,

                status=
                    Residents.Status.PENDING,

                supporting_document=
                    supporting_document
            )

            # ==================================================
            # SAVE COMPLETED PDF
            # ==================================================

            with open(
                completed_pdf,
                "rb"
            ) as pdf_file:

                resident.document.save(

                    os.path.basename(
                        completed_pdf
                    ),

                    File(
                        pdf_file
                    ),

                    save=True
                )

        # ======================================================
        # SUCCESS
        # ======================================================

        print("==========================================")
        print("TRANSFER SUCCESS")
        print("==========================================")

        print(
            "Resident ID:",
            resident.id
        )

        print(
            "Tracking Number:",
            resident.tracking_number
        )

        print(
            "Name:",
            resident.full_name
        )

        print(
            "Document:",
            resident.document.name
        )

        if resident.supporting_document:

            print(
                "Supporting Document:",
                resident.supporting_document.name
            )

        print(
            "Status:",
            resident.status
        )

        print("==========================================")

        # ======================================================
        # CLEAN TEMP
        # ======================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError as cleanup_error:

            print(
                "Temp cleanup error:",
                cleanup_error
            )

        # ======================================================
        # SUCCESS MESSAGE
        # ======================================================

        messages.success(
            request,
            "Your Transfer of Registration application "
            "was submitted successfully."
        )

        # ======================================================
        # SUCCESS PAGE
        # ======================================================

        return redirect(
            "success",
            resident.id
        )

    # ==========================================================
    # DATABASE ERROR
    # ==========================================================

    except IntegrityError as error:

        print("==========================================")
        print("TRANSFER DATABASE INTEGRITY ERROR")
        print("==========================================")

        print(
            "Error:",
            repr(error)
        )

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass

        messages.error(
            request,
            "An active Transfer application already exists "
            "for this resident."
        )

        return redirect(
            "transfer"
        )

    # ==========================================================
    # OTHER ERROR
    # ==========================================================

    except Exception as error:

        print("==========================================")
        print("TRANSFER ERROR")
        print("==========================================")

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            repr(error)
        )

        print("==========================================")

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass

        try:

            if os.path.exists(
                completed_pdf
            ):

                os.remove(
                    completed_pdf
                )

        except OSError:

            pass

        messages.error(
            request,
            "Unable to process your Transfer application. "
            "Please try again."
        )

        return redirect(
            "transfer"
        )
def reactivation(request):

    print("==========================================")
    print("REACTIVATION CALLED")
    print("METHOD:", request.method)
    print("==========================================")


    # =========================================================
    # GET
    # =========================================================

    if request.method == "GET":

        return render(
            request,
            "pages/reactivation.html"
        )


    # =========================================================
    # ONLY POST
    # =========================================================

    if request.method != "POST":

        return redirect(
            "reactivation"
        )


    # =========================================================
    # FORM DATA
    # =========================================================

    full_name = " ".join(
        request.POST.get(
            "full_name",
            ""
        ).strip().split()
    )


    contact_number = request.POST.get(
        "contact_number",
        ""
    ).strip()


    agreement = request.POST.get(
        "agreement",
        ""
    )


    # =========================================================
    # SUPPORTING DOCUMENTS
    #
    # IMPORTANT:
    #
    # HTML uses:
    #
    # name="document"
    #
    # Therefore backend MUST use:
    #
    # request.FILES.getlist("document")
    # =========================================================

    documents = request.FILES.getlist(
        "document"
    )


    supporting_document = (
        documents[0]
        if documents
        else None
    )


    # =========================================================
    # PDF ELEMENTS
    # =========================================================

    pdf_elements_raw = request.POST.get(
        "pdf_elements",
        "[]"
    )


    try:

        pdf_elements = json.loads(
            pdf_elements_raw
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        print(
            "INVALID PDF ELEMENT JSON"
        )

        pdf_elements = []


    if not isinstance(
        pdf_elements,
        list
    ):

        pdf_elements = []


    # =========================================================
    # DEBUG
    # =========================================================

    print()
    print("======================================")
    print("REACTIVATION APPLICATION")
    print("Applicant:", full_name)
    print("Contact:", contact_number)
    print("Agreement:", agreement)
    print(
        "Document Count:",
        len(documents)
    )

    for document in documents:

        print(
            "Document:",
            document.name,
            "| Size:",
            document.size
        )


    print(
        "RAW PDF ELEMENTS:",
        pdf_elements_raw
    )


    print(
        "PARSED PDF ELEMENTS:",
        pdf_elements
    )


    print(
        "PDF ELEMENT COUNT:",
        len(pdf_elements)
    )

    print("======================================")


    # =========================================================
    # VALIDATION
    # =========================================================

    if not full_name:

        messages.error(
            request,
            "Full name is required."
        )

        return redirect(
            "reactivation"
        )


    if not contact_number:

        messages.error(
            request,
            "Contact number is required."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # CONTACT VALIDATION
    # =========================================================

    if (
        len(contact_number) != 10
        or not contact_number.isdigit()
        or not contact_number.startswith("9")
    ):

        messages.error(
            request,
            "Please enter a valid 10-digit mobile number starting with 9."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # AGREEMENT
    # =========================================================

    if agreement != "on":

        messages.error(
            request,
            "You must agree before submitting."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # SUPPORTING DOCUMENT
    # =========================================================

    if not documents:

        messages.error(
            request,
            "Please upload at least one supporting document."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # FILE SIZE
    # =========================================================

    MAX_FILE_SIZE = (
        10 * 1024 * 1024
    )


    total_file_size = sum(
        document.size
        for document in documents
    )


    if total_file_size > MAX_FILE_SIZE:

        messages.error(
            request,
            "Supporting documents must not exceed 10MB."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # EXISTING REACTIVATION
    # =========================================================

    existing = Residents.objects.filter(

        full_name__iexact=full_name,

        document_type=(
            Residents.DocumentType.REACTIVATION
        )

    ).first()


    print(
        "EXISTING REACTIVATION:",
        existing
    )


    # =========================================================
    # EXISTING APPLICATION
    # =========================================================

    if existing:

        print(
            "EXISTING STATUS:",
            existing.status
        )


        # -----------------------------------------------------
        # PENDING
        # -----------------------------------------------------

        if (
            existing.status ==
            Residents.Status.PENDING
        ):

            messages.error(
                request,
                "You already have a pending Reactivation application."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        # -----------------------------------------------------
        # APPROVED
        # -----------------------------------------------------

        elif (
            existing.status ==
            Residents.Status.APPROVED
        ):

            messages.error(
                request,
                "Your Reactivation application has already been approved."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        # -----------------------------------------------------
        # DUPLICATE
        # -----------------------------------------------------

        elif (
            existing.status ==
            Residents.Status.DUPLICATION
        ):

            messages.error(
                request,
                "Your Reactivation application was marked as a duplicate."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        # -----------------------------------------------------
        # REJECTED
        #
        # Allow resubmission.
        # -----------------------------------------------------

        elif (
            hasattr(
                Residents.Status,
                "REJECTED"
            )
            and
            existing.status ==
            Residents.Status.REJECTED
        ):

            print(
                "Previous Reactivation application was rejected."
            )

            print(
                "Applicant is allowed to submit again."
            )

            # Remove rejected application so that
            # unique constraints do not interfere.
            existing.delete()


    # =========================================================
    # OFFICIAL REACTIVATION PDF
    # =========================================================

    reactivation_pdf = os.path.join(

        settings.BASE_DIR,

        "core",

        "static",

        "docs",

        "Request_for_Reactivation_Pioduran_Online_Registration.pdf"

    )


    print("==========================================")
    print("REACTIVATION PDF")
    print(
        "PDF:",
        reactivation_pdf
    )
    print(
        "Exists:",
        os.path.exists(
            reactivation_pdf
        )
    )
    print("==========================================")


    if not os.path.isfile(
        reactivation_pdf
    ):

        messages.error(
            request,
            "The Reactivation PDF could not be found."
        )

        return redirect(
            "reactivation"
        )


    # =========================================================
    # SAFE APPLICANT NAME
    # =========================================================

    safe_name = "".join(

        character

        for character in full_name

        if (
            character.isalnum()
            or character in (
                " ",
                "-",
                "_"
            )
        )

    ).strip()


    safe_name = "_".join(
        safe_name.split()
    )


    if not safe_name:

        safe_name = "resident"


    # =========================================================
    # DIRECTORIES
    # =========================================================

    completed_directory = os.path.join(

        settings.MEDIA_ROOT,

        "completed_applications"

    )


    os.makedirs(

        completed_directory,

        exist_ok=True

    )


    completed_pdf = os.path.join(

        completed_directory,

        f"{safe_name}_REACTIVATION.pdf"

    )


    temp_directory = os.path.join(

        settings.MEDIA_ROOT,

        "temp_pdf"

    )


    os.makedirs(

        temp_directory,

        exist_ok=True

    )


    temp_original = os.path.join(

        temp_directory,

        f"{safe_name}_reactivation_source.pdf"

    )


    # =========================================================
    # REMOVE OLD TEMP FILE
    # =========================================================

    try:

        if os.path.exists(
            temp_original
        ):

            os.remove(
                temp_original
            )

    except OSError:

        pass


    # =========================================================
    # PROCESS PDF
    # =========================================================

    try:

        # =====================================================
        # COPY ORIGINAL PDF
        # =====================================================

        print(
            "Copying original Reactivation PDF..."
        )


        with open(
            reactivation_pdf,
            "rb"
        ) as source:

            with open(
                temp_original,
                "wb"
            ) as destination:

                while True:

                    chunk = source.read(
                        1024 * 1024
                    )

                    if not chunk:

                        break

                    destination.write(
                        chunk
                    )


        # =====================================================
        # GENERATE FILLED PDF
        # =====================================================

        print(
            "Generating filled Reactivation PDF..."
        )


        print(
            "ELEMENTS SENT TO PDF GENERATOR:",
            pdf_elements
        )


        generate_filled_pdf(

            original_pdf=temp_original,

            elements=pdf_elements,

            output_path=completed_pdf

        )


        # =====================================================
        # VERIFY GENERATED PDF
        # =====================================================

        if not os.path.exists(
            completed_pdf
        ):

            raise Exception(
                "Completed PDF was not generated."
            )


        print(
            "COMPLETED PDF:",
            completed_pdf
        )


        print(
            "COMPLETED PDF SIZE:",
            os.path.getsize(
                completed_pdf
            )
        )


        # =====================================================
        # DATABASE
        # =====================================================

        with transaction.atomic():

            resident = Residents.objects.create(

                full_name=full_name,

                contact_number=contact_number,

                document_type=(
                    Residents.DocumentType.REACTIVATION
                ),

                status=(
                    Residents.Status.PENDING
                ),

            )


            # =================================================
            # SAVE COMPLETED REACTIVATION PDF
            #
            # This becomes resident.document
            # =================================================

            with open(
                completed_pdf,
                "rb"
            ) as pdf_file:

                resident.document.save(

                    os.path.basename(
                        completed_pdf
                    ),

                    File(
                        pdf_file
                    ),

                    save=True

                )


            # =================================================
            # SAVE SUPPORTING DOCUMENT
            # =================================================

            if supporting_document:

                resident.supporting_document = (
                    supporting_document
                )

                resident.save(
                    update_fields=[
                        "supporting_document"
                    ]
                )


            # =================================================
            # SAVE PDF ELEMENTS
            # =================================================

            if hasattr(
                resident,
                "pdf_elements"
            ):

                resident.pdf_elements = (
                    pdf_elements
                )

                resident.save(
                    update_fields=[
                        "pdf_elements"
                    ]
                )


        # =====================================================
        # SUCCESS DEBUG
        # =====================================================

        print("==========================================")
        print("REACTIVATION SUCCESS")
        print(
            "Resident:",
            resident.id
        )

        print(
            "Tracking:",
            resident.tracking_number
        )

        print(
            "Completed PDF:",
            resident.document.name
        )

        print(
            "Supporting Document:",
            getattr(
                resident,
                "supporting_document",
                None
            )
        )

        print(
            "PDF Elements:",
            getattr(
                resident,
                "pdf_elements",
                []
            )
        )

        print(
            "PDF Element Count:",
            len(
                getattr(
                    resident,
                    "pdf_elements",
                    []
                )
            )
        )

        print("==========================================")


        # =====================================================
        # DELETE TEMP PDF
        # =====================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        # =====================================================
        # SUCCESS MESSAGE
        # =====================================================

        messages.success(

            request,

            "Your Reactivation application was submitted successfully."

        )


        return redirect(

            "success",

            resident.id

        )


    # =========================================================
    # DATABASE ERROR
    # =========================================================

    except IntegrityError as error:

        print(
            "DATABASE ERROR:",
            repr(error)
        )


        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        messages.error(

            request,

            "An active Reactivation application already exists."

        )


        return redirect(
            "reactivation"
        )


    # =========================================================
    # OTHER ERROR
    # =========================================================

    except Exception as error:

        print("==========================================")

        print(
            "REACTIVATION ERROR"
        )

        print(
            "TYPE:",
            type(error).__name__
        )

        print(
            "ERROR:",
            repr(error)
        )

        print("==========================================")


        # -----------------------------------------------------
        # REMOVE TEMP SOURCE
        # -----------------------------------------------------

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        # -----------------------------------------------------
        # REMOVE GENERATED PDF
        # -----------------------------------------------------

        try:

            if os.path.exists(
                completed_pdf
            ):

                os.remove(
                    completed_pdf
                )

        except OSError:

            pass


        messages.error(

            request,

            "Unable to process your Reactivation application."

        )


        return redirect(
            "reactivation"
        )
def update_info(request):

    print("==========================================")
    print("UPDATE INFORMATION CALLED")
    print("METHOD:", request.method)
    print("==========================================")


    # =========================================================
    # GET
    # =========================================================

    if request.method == "GET":

        return render(
            request,
            "pages/update_info.html"
        )


    if request.method != "POST":

        return redirect(
            "update_info"
        )


    # =========================================================
    # FORM DATA
    # =========================================================

    full_name = " ".join(
        request.POST.get(
            "full_name",
            ""
        ).strip().split()
    )


    contact_number = request.POST.get(
        "contact_number",
        ""
    ).strip()


    agreement = request.POST.get(
        "agreement",
        ""
    )


    # =========================================================
    # SUPPORTING DOCUMENTS
    # =========================================================

    supporting_documents = request.FILES.getlist(
        "supporting_document"
    )


    # =========================================================
    # PDF ELEMENTS
    # =========================================================

    pdf_elements_raw = request.POST.get(
        "pdf_elements",
        "[]"
    )


    try:

        pdf_elements = json.loads(
            pdf_elements_raw
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        print(
            "INVALID PDF ELEMENT JSON"
        )

        pdf_elements = []


    if not isinstance(
        pdf_elements,
        list
    ):

        pdf_elements = []


    # =========================================================
    # DEBUG
    # =========================================================

    print()
    print("======================================")
    print("UPDATE APPLICATION")
    print("Applicant:", full_name)
    print("Contact:", contact_number)
    print("Agreement:", agreement)

    print(
        "Supporting Document Count:",
        len(supporting_documents)
    )

    for document in supporting_documents:

        print(
            "Supporting Document:",
            document.name,
            "| Size:",
            document.size
        )


    print(
        "RAW PDF ELEMENTS:",
        pdf_elements_raw
    )

    print(
        "PARSED PDF ELEMENTS:",
        pdf_elements
    )

    print(
        "PDF ELEMENT COUNT:",
        len(pdf_elements)
    )

    print("======================================")


    # =========================================================
    # VALIDATION
    # =========================================================

    if not full_name:

        messages.error(
            request,
            "Full name is required."
        )

        return redirect(
            "update_info"
        )


    if not contact_number:

        messages.error(
            request,
            "Contact number is required."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # CONTACT VALIDATION
    # =========================================================

    if (
        len(contact_number) != 10
        or not contact_number.isdigit()
        or not contact_number.startswith("9")
    ):

        messages.error(
            request,
            "Please enter a valid 10-digit mobile number starting with 9."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # AGREEMENT
    # =========================================================

    if agreement != "on":

        messages.error(
            request,
            "You must agree before submitting."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # SUPPORTING DOCUMENT
    # =========================================================

    if not supporting_documents:

        messages.error(
            request,
            "Please upload at least one supporting document."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # FILE SIZE
    # =========================================================

    MAX_FILE_SIZE = (
        10 * 1024 * 1024
    )


    total_file_size = sum(
        document.size
        for document in supporting_documents
    )


    if total_file_size > MAX_FILE_SIZE:

        messages.error(
            request,
            "Supporting documents must not exceed 10MB."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # EXISTING APPLICATION
    # =========================================================

    existing = Residents.objects.filter(

        full_name__iexact=full_name,

        document_type=(
            Residents.DocumentType.UPDATE
        )

    ).first()


    print(
        "EXISTING UPDATE:",
        existing
    )


    if existing:

        if (
            existing.status ==
            Residents.Status.PENDING
        ):

            messages.error(
                request,
                "You already have a pending Update application."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        elif (
            existing.status ==
            Residents.Status.APPROVED
        ):

            messages.error(
                request,
                "Your Update application has already been approved."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        elif (
            existing.status ==
            Residents.Status.DUPLICATION
        ):

            messages.error(
                request,
                "Your Update application was marked as a duplicate."
            )

            return redirect(
                "already_registered",
                existing.id
            )


        elif (
            hasattr(
                Residents.Status,
                "REJECTED"
            )
            and
            existing.status ==
            Residents.Status.REJECTED
        ):

            print(
                "Previous Update application was rejected."
            )

            existing.delete()


    # =========================================================
    # OFFICIAL CEF-1 PDF
    # =========================================================

    original_pdf = os.path.join(

        settings.BASE_DIR,

        "core",

        "static",

        "docs",

        "com_res_11177_annexB.pdf"

    )


    print("==========================================")
    print("CEF-1 PDF")
    print("PDF:", original_pdf)
    print(
        "Exists:",
        os.path.exists(original_pdf)
    )
    print("==========================================")


    if not os.path.isfile(
        original_pdf
    ):

        messages.error(
            request,
            "The CEF-1 application PDF could not be found."
        )

        return redirect(
            "update_info"
        )


    # =========================================================
    # SAFE NAME
    # =========================================================

    safe_name = "".join(

        character

        for character in full_name

        if (
            character.isalnum()
            or character in (
                " ",
                "-",
                "_"
            )
        )

    ).strip()


    safe_name = "_".join(
        safe_name.split()
    )


    if not safe_name:

        safe_name = "resident"


    # =========================================================
    # DIRECTORIES
    # =========================================================

    completed_directory = os.path.join(

        settings.MEDIA_ROOT,

        "completed_applications"

    )


    os.makedirs(
        completed_directory,
        exist_ok=True
    )


    completed_pdf = os.path.join(

        completed_directory,

        f"{safe_name}_UPDATE.pdf"

    )


    temp_directory = os.path.join(

        settings.MEDIA_ROOT,

        "temp_pdf"

    )


    os.makedirs(
        temp_directory,
        exist_ok=True
    )


    temp_original = os.path.join(

        temp_directory,

        f"{safe_name}_update_source.pdf"

    )


    # =========================================================
    # PROCESS PDF
    # =========================================================

    try:

        # -----------------------------------------------------
        # COPY ORIGINAL PDF
        # -----------------------------------------------------

        with open(
            original_pdf,
            "rb"
        ) as source:

            with open(
                temp_original,
                "wb"
            ) as destination:

                while True:

                    chunk = source.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    destination.write(
                        chunk
                    )


        # -----------------------------------------------------
        # GENERATE FILLED PDF
        # -----------------------------------------------------

        print(
            "Generating filled CEF-1 PDF..."
        )


        print(
            "ELEMENTS SENT TO PDF GENERATOR:",
            pdf_elements
        )


        generate_filled_pdf(

            original_pdf=temp_original,

            elements=pdf_elements,

            output_path=completed_pdf

        )


        # -----------------------------------------------------
        # VERIFY
        # -----------------------------------------------------

        if not os.path.exists(
            completed_pdf
        ):

            raise Exception(
                "Completed CEF-1 PDF was not generated."
            )


        print(
            "COMPLETED PDF:",
            completed_pdf
        )


        print(
            "COMPLETED PDF SIZE:",
            os.path.getsize(
                completed_pdf
            )
        )


        # =====================================================
        # DATABASE
        # =====================================================

        with transaction.atomic():

            resident = Residents.objects.create(

                full_name=full_name,

                contact_number=contact_number,

                document_type=(
                    Residents.DocumentType.UPDATE
                ),

                status=(
                    Residents.Status.PENDING
                ),

            )


            # -------------------------------------------------
            # SAVE GENERATED CEF-1
            # -------------------------------------------------

            with open(
                completed_pdf,
                "rb"
            ) as pdf_file:

                resident.document.save(

                    os.path.basename(
                        completed_pdf
                    ),

                    File(
                        pdf_file
                    ),

                    save=True

                )


            # -------------------------------------------------
            # SAVE SUPPORTING DOCUMENTS
            #
            # If your model has only one supporting_document
            # field, save the first document.
            # -------------------------------------------------

            if supporting_documents:

                resident.supporting_document = (
                    supporting_documents[0]
                )

                resident.save(
                    update_fields=[
                        "supporting_document"
                    ]
                )


            # -------------------------------------------------
            # SAVE PDF ELEMENTS
            # -------------------------------------------------

            if hasattr(
                resident,
                "pdf_elements"
            ):

                resident.pdf_elements = (
                    pdf_elements
                )

                resident.save(
                    update_fields=[
                        "pdf_elements"
                    ]
                )


        # =====================================================
        # SUCCESS
        # =====================================================

        print("==========================================")
        print("UPDATE APPLICATION SUCCESS")
        print(
            "Resident:",
            resident.id
        )

        print(
            "Tracking:",
            resident.tracking_number
        )

        print(
            "Completed PDF:",
            resident.document.name
        )

        print(
            "PDF Elements:",
            getattr(
                resident,
                "pdf_elements",
                []
            )
        )

        print(
            "PDF Element Count:",
            len(
                getattr(
                    resident,
                    "pdf_elements",
                    []
                )
            )
        )

        print("==========================================")


        # =====================================================
        # DELETE TEMP
        # =====================================================

        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        messages.success(

            request,

            "Your Correction / Update application was submitted successfully."

        )


        return redirect(
            "success",
            resident.id
        )


    # =========================================================
    # DATABASE ERROR
    # =========================================================

    except IntegrityError as error:

        print(
            "DATABASE ERROR:",
            repr(error)
        )


        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        messages.error(
            request,
            "An active Update application already exists."
        )


        return redirect(
            "update_info"
        )


    # =========================================================
    # OTHER ERROR
    # =========================================================

    except Exception as error:

        print("==========================================")
        print("UPDATE INFORMATION ERROR")
        print(
            "TYPE:",
            type(error).__name__
        )
        print(
            "ERROR:",
            repr(error)
        )
        print("==========================================")


        try:

            if os.path.exists(
                temp_original
            ):

                os.remove(
                    temp_original
                )

        except OSError:

            pass


        try:

            if os.path.exists(
                completed_pdf
            ):

                os.remove(
                    completed_pdf
                )

        except OSError:

            pass


        messages.error(
            request,
            "Unable to process your Correction / Update application."
        )


        return redirect(
            "update_info"
        )

def reinstatement(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        pdf_elements = request.POST.get("pdf_elements", "").strip()

        application_files = request.FILES.getlist("application_files")

        # ==========================================
        # VALIDATION
        # ==========================================

        if not full_name:
            messages.error(
                request,
                "Full name is required."
            )
            return redirect("reinstatement")

        if not pdf_elements:
            messages.error(
                request,
                "Please complete the reinstatement form before submitting."
            )
            return redirect("reinstatement")

        # ==========================================
        # CHECK DUPLICATE APPLICATION
        # ==========================================

        existing = Residents.objects.filter(
            full_name__iexact=full_name,
            document_type=Residents.DocumentType.REINSTATEMENT
        ).first()

        if existing:

            if existing.status == Residents.Status.PENDING:

                messages.error(
                    request,
                    "You already have a pending Reinstatement application."
                )

                return redirect(
                    "already_registered",
                    existing.id
                )

            elif existing.status == Residents.Status.APPROVED:

                messages.error(
                    request,
                    "Your Reinstatement application has already been approved."
                )

                return redirect(
                    "already_registered",
                    existing.id
                )

            elif existing.status == Residents.Status.DUPLICATION:

                messages.error(
                    request,
                    "Your Reinstatement application was marked as a duplicate."
                )

                return redirect(
                    "already_registered",
                    existing.id
                )

        # ==========================================
        # FIND APPLICATION PDF
        # ==========================================

        application_pdf = os.path.join(
            "static",
            "docs",
            "Request_for_Inclusion_or_Reinstatement_in_the_List_of_Voters.pdf"
        )

        # ==========================================
        # GENERATE COMPLETED PDF
        # ==========================================

        try:

            completed_pdf = generate_filled_pdf(
                application_pdf,
                pdf_elements
            )

        except Exception as e:

            messages.error(
                request,
                f"Unable to generate the completed application PDF: {e}"
            )

            return redirect("reinstatement")

        # ==========================================
        # CREATE RESIDENT
        # ==========================================

        resident = Residents.objects.create(
            full_name=full_name,
            document_type=Residents.DocumentType.REINSTATEMENT,
        )

        # ==========================================
        # SAVE COMPLETED PDF
        # ==========================================

        safe_name = "".join(
            c if c.isalnum() or c in "._-" else "_"
            for c in full_name
        )

        filename = f"{safe_name}_REINSTATEMENT.pdf"

        resident.document.save(
            filename,
            ContentFile(completed_pdf),
            save=False
        )

        # ==========================================
        # SAVE SUPPORTING DOCUMENT
        # ==========================================

        if application_files:

            # First uploaded supporting file.
            # This follows the same storage pattern
            # currently used by your other services.

            supporting_file = application_files[0]

            resident.supporting_document.save(
                supporting_file.name,
                supporting_file,
                save=False
            )

        # ==========================================
        # SAVE RESIDENT
        # ==========================================

        resident.save()

        # ==========================================
        # SUCCESS
        # ==========================================

        return redirect(
            "success",
            resident.id
        )

    return render(
        request,
        "pages/reinstatement.html"
    )

def success(request, resident_id):
    resident = get_object_or_404(Residents, id=resident_id)

    return render(
        request,
        "components/success.html",
        {
            "resident": resident
        }
    )

def already_registered(request, resident_id):
    resident = get_object_or_404(Residents, id=resident_id)

    return render(
        request,
        "components/existing_submission.html",
        {
            "resident": resident
        }
    )

def login_view(request):
    create_default_admin()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'resident':
                return redirect('controller_dashboard')
            else:
                return redirect('login')

        return redirect('login')

    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def admin_dashboard(request):
    return render(request, 'core/dashboard.html')

@login_required
def new_registration_view(request):

    pending = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status=Residents.Status.PENDING
    ).order_by("-created_at")

    pre_approved = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status=Residents.Status.PRE_APPROVED
    ).order_by("-created_at")

    # approved = Residents.objects.filter(
    #     document_type=Residents.DocumentType.NEW_REGISTRATION,
    #     status=Residents.Status.APPROVED
    # ).order_by("-created_at")

    rejected = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status__in=[
            Residents.Status.REJECTED,
            Residents.Status.DUPLICATION,
        ]
    ).order_by("-created_at")

    context = {
        "pending": pending,
        "pre_approved": pre_approved,
        # "approved": approved,
        "rejected": rejected,

        "pending_count": pending.count(),
        "pre_approved_count": pre_approved.count(),
        # "approved_count": approved.count(),
        "rejected_count": rejected.count(),
    }

    return render(
        request,
        "core/new_registrations.html",
        context
    )

@login_required
def pre_approve(request, pk):

    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    resident.status = Residents.Status.PRE_APPROVED
    resident.save()

    return redirect("registration-view")


@login_required
def capture_thumbmark(request, pk):

    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    if request.method == "POST":

        thumb = request.FILES.get("thumb_mark")

        if thumb:

            resident.thumb_mark = thumb
            resident.status = Residents.Status.APPROVED
            resident.biometric_date = timezone.now()
            resident.captured_by = request.user

            resident.save()

            return redirect("registration-view")

    return render(
        request,
        "core/capture_thumbmark.html",
        {
            "resident": resident
        }
    )

@login_required
def reject_registration(request, pk):
    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    if request.method == "POST":
        remarks = request.POST.get("remarks", "").strip()

        if not remarks:
            messages.error(request, "Please provide a reason for rejection.")
            return redirect("reject_registration", pk=resident.id)

        resident.status = Residents.Status.REJECTED
        resident.remarks = remarks
        resident.save()

        messages.success(
            request,
            f"{resident.full_name}'s application has been rejected."
        )

        return redirect("registration-view")

    return render(
        request,
        "core/reject_registration.html",
        {
            "resident": resident
        }
    )

@login_required
def transfers(request):

    pending = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status=Residents.Status.PENDING
    ).order_by("-created_at")

    approved = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status=Residents.Status.APPROVED
    ).order_by("-created_at")

    rejected = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status__in=[
            Residents.Status.REJECTED,
            Residents.Status.DUPLICATION,
        ]
    ).order_by("-created_at")

    context = {
        "transfers": pending,
        "approved_transfers": approved,
        "rejected_transfers": rejected,

        "pending_count": pending.count(),
        "approved_count": approved.count(),
        "rejected_count": rejected.count(),
    }

    return render(
        request,
        "core/incoming_transfers.html",
        context
    )

@login_required
def voter_reactivation(request):
    return render(request, 'core/voter_reactivation.html')

@login_required
def voter_correction(request):
    return render(request, 'core/voter_correction.html')

@login_required
def voter_reinstatement(request):
    return render(request, 'core/voter_reinstatement.html')

@login_required
def audit_logs(request):
    residents_list = Residents.objects.filter(
        status=Residents.Status.APPROVED
        ).order_by("-created_at")
    
    return render(request, 'core/audit_logs.html',{'residents_list': residents_list})