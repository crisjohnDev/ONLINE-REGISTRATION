import * as pdfjsLib from
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.min.mjs";


// ==========================================================
// CONFIG
// ==========================================================

const PDF_URL = window.PDF_URL;

const pdfPages =
    document.getElementById("pdfPages");

const pdfToolbar =
    document.getElementById("pdfToolbar");

const editorStatus =
    document.getElementById("editorStatus");


// ==========================================================
// PDF.JS WORKER
// ==========================================================

pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs";


// ==========================================================
// STATE
// ==========================================================

let pdfDocument = null;

let currentTool = "select";

let elements = [];

let selectedElement = null;

let elementCounter = 0;

let signatureTarget = null;

let signatureDrawing = false;


// ==========================================================
// STATUS
// ==========================================================

function setStatus(message) {

    if (editorStatus) {

        editorStatus.textContent = message;

    }

    console.log("[PDF EDITOR]", message);
}


// ==========================================================
// LOAD PDF
// ==========================================================

async function loadPDF() {

    if (!PDF_URL) {

        console.error("PDF URL is missing.");

        setStatus("PDF URL is missing.");

        return;
    }

    try {

        setStatus("Loading CEF-1...");

        pdfDocument =
            await pdfjsLib
                .getDocument(PDF_URL)
                .promise;


        console.log(
            "CEF-1 PDF loaded:",
            pdfDocument.numPages,
            "pages"
        );


        pdfPages.innerHTML = "";


        for (
            let pageNumber = 1;
            pageNumber <= pdfDocument.numPages;
            pageNumber++
        ) {

            await renderPage(pageNumber);

        }


        setStatus(
            `${pdfDocument.numPages} page(s) ready.`
        );


    } catch (error) {

        console.error(
            "PDF loading error:",
            error
        );

        setStatus(
            "Unable to load the PDF."
        );

        alert(
            "Unable to load the CEF-1 PDF."
        );
    }
}


// ==========================================================
// RENDER PAGE
// ==========================================================

async function renderPage(pageNumber) {

    const page =
        await pdfDocument.getPage(
            pageNumber
        );


    // ======================================================
    // ORIGINAL PDF SIZE
    // ======================================================

    const originalViewport =
        page.getViewport({
            scale: 1
        });


    // ======================================================
    // EDITOR WIDTH
    // ======================================================

    const editor =
        document.getElementById(
            "pdfEditor"
        );


    let availableWidth =
        editor
            ? editor.clientWidth - 40
            : originalViewport.width;


    if (availableWidth <= 0) {

        availableWidth =
            originalViewport.width;

    }


    // ======================================================
    // SCALE
    // ======================================================

    let scale =
        availableWidth /
        originalViewport.width;


    scale =
        Math.min(
            scale,
            1.50
        );


    scale =
        Math.max(
            scale,
            0.50
        );


    const viewport =
        page.getViewport({
            scale: scale
        });


    // ======================================================
    // PAGE CONTAINER
    // ======================================================

    const pageContainer =
        document.createElement(
            "div"
        );


    pageContainer.className =
        "pdf-page";


    /*
     * IMPORTANT
     *
     * page is ZERO BASED.
     *
     * First PDF page = 0
     * Second PDF page = 1
     */

    pageContainer.dataset.page =
        pageNumber - 1;


    pageContainer.dataset.pdfPage =
        pageNumber;


    pageContainer.dataset.scale =
        scale;


    pageContainer.dataset.pdfWidth =
        originalViewport.width;


    pageContainer.dataset.pdfHeight =
        originalViewport.height;


    pageContainer.style.width =
        `${viewport.width}px`;


    pageContainer.style.height =
        `${viewport.height}px`;


    // ======================================================
    // CANVAS
    // ======================================================

    const canvas =
        document.createElement(
            "canvas"
        );


    const context =
        canvas.getContext("2d");


    canvas.width =
        viewport.width;


    canvas.height =
        viewport.height;


    canvas.className =
        "pdf-canvas";


    pageContainer.appendChild(
        canvas
    );


    // ======================================================
    // ELEMENT LAYER
    // ======================================================

    const elementLayer =
        document.createElement(
            "div"
        );


    elementLayer.className =
        "pdf-element-layer";


    pageContainer.appendChild(
        elementLayer
    );


    // ======================================================
    // ADD PAGE
    // ======================================================

    pdfPages.appendChild(
        pageContainer
    );


    // ======================================================
    // RENDER PDF
    // ======================================================

    await page.render({

        canvasContext:
            context,

        viewport:
            viewport

    }).promise;


    console.log(
        "Rendered page:",
        pageNumber,
        "PDF coordinates:",
        originalViewport.width,
        "x",
        originalViewport.height,
        "display:",
        viewport.width,
        "x",
        viewport.height,
        "scale:",
        scale
    );
}


// ==========================================================
// TOOL
// ==========================================================

function setTool(tool) {

    currentTool = tool;


    document
        .querySelectorAll(
            ".pdf-tool[data-tool]"
        )
        .forEach(button => {

            button.classList.remove(
                "active-tool"
            );

        });


    const button =
        document.querySelector(
            `.pdf-tool[data-tool="${tool}"]`
        );


    if (button) {

        button.classList.add(
            "active-tool"
        );

    }


    setStatus(
        tool === "select"
            ? "Select an element."
            : `Tool selected: ${tool}`
    );
}


// ==========================================================
// TOOLBAR
// ==========================================================

if (pdfToolbar) {

    pdfToolbar.addEventListener(
        "click",
        function(event) {

            const button =
                event.target.closest(
                    "button"
                );


            if (!button) {

                return;

            }


            const tool =
                button.dataset.tool;


            if (tool) {

                setTool(tool);

            }

        }
    );
}


// ==========================================================
// PDF CLICK
// ==========================================================

if (pdfPages) {

    pdfPages.addEventListener(
        "click",
        function(event) {

            const page =
                event.target.closest(
                    ".pdf-page"
                );


            if (!page) {

                return;

            }


            const existingElement =
                event.target.closest(
                    ".pdf-element"
                );


            // ==================================================
            // SELECT EXISTING
            // ==================================================

            if (existingElement) {

                const id =
                    Number(
                        existingElement.dataset.id
                    );


                const data =
                    elements.find(
                        item =>
                            item.id === id
                    );


                if (data) {

                    selectElement(
                        existingElement,
                        data
                    );

                }


                return;
            }


            // ==================================================
            // CLICK POSITION
            // ==================================================

            const rect =
                page.getBoundingClientRect();


            const x =
                event.clientX -
                rect.left;


            const y =
                event.clientY -
                rect.top;


            // ==================================================
            // TOOL
            // ==================================================

            if (currentTool === "text") {

                addText(
                    page,
                    x,
                    y
                );


            } else if (currentTool === "check") {

                addCheck(
                    page,
                    x,
                    y
                );


            } else if (currentTool === "cross") {

                addCross(
                    page,
                    x,
                    y
                );


            } else if (currentTool === "date") {

                addDate(
                    page,
                    x,
                    y
                );


            } else if (currentTool === "signature") {

                openSignatureModal(
                    page,
                    x,
                    y
                );

            }

        }
    );
}


// ==========================================================
// CREATE ELEMENT
// ==========================================================

function createElement(
    page,
    type,
    x,
    y
) {

    elementCounter++;


    const element =
        document.createElement(
            "div"
        );


    element.className =
        "pdf-element";


    element.dataset.id =
        elementCounter;


    element.dataset.type =
        type;


    element.dataset.page =
        page.dataset.page;


    element.style.left =
        `${x}px`;


    element.style.top =
        `${y}px`;


    page
        .querySelector(
            ".pdf-element-layer"
        )
        .appendChild(
            element
        );


    const scale =
        Number(
            page.dataset.scale
        ) || 1;


    const pdfWidth =
        Number(
            page.dataset.pdfWidth
        ) || 0;


    const pdfHeight =
        Number(
            page.dataset.pdfHeight
        ) || 0;


    const data = {

        id:
            elementCounter,

        type:
            type,

        /*
         * ZERO-BASED PAGE
         */
        page:
            Number(
                page.dataset.page
            ),

        x:
            Number(x),

        y:
            Number(y),

        width:
            0,

        height:
            0,

        value:
            "",

        scale:
            scale,

        /*
         * Actual PDF dimensions
         */
        pageWidth:
            pdfWidth,

        pageHeight:
            pdfHeight

    };


    elements.push(data);


    makeDraggable(
        element,
        data
    );


    selectElement(
        element,
        data
    );


    return {
        element,
        data
    };
}


// ==========================================================
// TEXT
// ==========================================================

function addText(
    page,
    x,
    y
) {

    const value =
        prompt(
            "Enter text:"
        );


    if (
        !value ||
        !value.trim()
    ) {

        return;

    }


    const result =
        createElement(
            page,
            "text",
            x,
            y
        );


    result.element.textContent =
        value.trim();


    result.element.classList.add(
        "text-element"
    );


    result.data.value =
        value.trim();


    result.data.fontSize =
        14;


    updateDimensions(
        result.element,
        result.data
    );


    setStatus(
        "Text added."
    );
}


// ==========================================================
// CHECK
// ==========================================================

function addCheck(
    page,
    x,
    y
) {

    const result =
        createElement(
            page,
            "check",
            x,
            y
        );


    result.element.textContent =
        "✓";


    result.element.classList.add(
        "check-element"
    );


    result.data.value =
        "✓";


    result.data.width =
        result.element.offsetWidth ||
        22;


    result.data.height =
        result.element.offsetHeight ||
        22;


    setStatus(
        "Checkmark added."
    );
}


// ==========================================================
// CROSS
// ==========================================================

function addCross(
    page,
    x,
    y
) {

    const result =
        createElement(
            page,
            "cross",
            x,
            y
        );


    result.element.textContent =
        "X";


    result.element.classList.add(
        "cross-element"
    );


    result.data.value =
        "X";


    result.data.width =
        result.element.offsetWidth ||
        22;


    result.data.height =
        result.element.offsetHeight ||
        22;


    setStatus(
        "X added."
    );
}


// ==========================================================
// DATE
// ==========================================================

function addDate(
    page,
    x,
    y
) {

    const date =
        new Date().toLocaleDateString(
            "en-PH"
        );


    const result =
        createElement(
            page,
            "date",
            x,
            y
        );


    result.element.textContent =
        date;


    result.element.classList.add(
        "date-element"
    );


    result.data.value =
        date;


    result.data.fontSize =
        13;


    updateDimensions(
        result.element,
        result.data
    );


    setStatus(
        "Date added."
    );
}


// ==========================================================
// DIMENSIONS
// ==========================================================

function updateDimensions(
    element,
    data
) {

    requestAnimationFrame(
        function() {

            const rect =
                element.getBoundingClientRect();


            data.width =
                rect.width;


            data.height =
                rect.height;

        }
    );
}


// ==========================================================
// SELECT
// ==========================================================

function selectElement(
    element,
    data
) {

    if (selectedElement) {

        selectedElement.classList.remove(
            "selected-element"
        );

    }


    selectedElement =
        element;


    element.classList.add(
        "selected-element"
    );


    setStatus(
        `${data.type} selected. Press Delete to remove.`
    );
}


// ==========================================================
// DRAG
// ==========================================================

function makeDraggable(
    element,
    data
) {

    let dragging = false;

    let startX = 0;

    let startY = 0;

    let originalX = 0;

    let originalY = 0;


    element.addEventListener(
        "mousedown",
        function(event) {

            event.preventDefault();

            event.stopPropagation();


            selectElement(
                element,
                data
            );


            dragging = true;


            startX =
                event.clientX;


            startY =
                event.clientY;


            originalX =
                parseFloat(
                    element.style.left
                ) || 0;


            originalY =
                parseFloat(
                    element.style.top
                ) || 0;

        }
    );


    document.addEventListener(
        "mousemove",
        function(event) {

            if (!dragging) {

                return;

            }


            const dx =
                event.clientX -
                startX;


            const dy =
                event.clientY -
                startY;


            const newX =
                originalX +
                dx;


            const newY =
                originalY +
                dy;


            element.style.left =
                `${newX}px`;


            element.style.top =
                `${newY}px`;


            data.x =
                newX;


            data.y =
                newY;

        }
    );


    document.addEventListener(
        "mouseup",
        function() {

            dragging = false;

        }
    );
}


// ==========================================================
// DELETE
// ==========================================================

function deleteSelected() {

    if (!selectedElement) {

        return;

    }


    const id =
        Number(
            selectedElement.dataset.id
        );


    elements =
        elements.filter(
            item =>
                item.id !== id
        );


    selectedElement.remove();


    selectedElement =
        null;


    setStatus(
        "Element deleted."
    );
}


const deleteButton =
    document.getElementById(
        "deleteElement"
    );


if (deleteButton) {

    deleteButton.addEventListener(
        "click",
        deleteSelected
    );
}


// ==========================================================
// KEYBOARD DELETE
// ==========================================================

document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Delete"
        ) {

            deleteSelected();

        }

    }
);


// ==========================================================
// SIGNATURE
// ==========================================================

const signatureModal =
    document.getElementById(
        "signatureModal"
    );


const signatureCanvas =
    document.getElementById(
        "signatureCanvas"
    );


const signatureContext =
    signatureCanvas
        ? signatureCanvas.getContext("2d")
        : null;


function openSignatureModal(
    page,
    x,
    y
) {

    signatureTarget = {

        page:
            page,

        x:
            x,

        y:
            y

    };


    clearSignature();


    if (signatureModal) {

        signatureModal.classList.remove(
            "hidden"
        );

    }
}


// ==========================================================
// SIGNATURE DRAWING
// ==========================================================

if (signatureCanvas) {

    signatureCanvas.addEventListener(
        "mousedown",
        function(event) {

            signatureDrawing =
                true;


            const rect =
                signatureCanvas.getBoundingClientRect();


            const scaleX =
                signatureCanvas.width /
                rect.width;


            const scaleY =
                signatureCanvas.height /
                rect.height;


            signatureContext.beginPath();


            signatureContext.moveTo(

                (
                    event.clientX -
                    rect.left
                ) * scaleX,

                (
                    event.clientY -
                    rect.top
                ) * scaleY

            );

        }
    );


    signatureCanvas.addEventListener(
        "mousemove",
        function(event) {

            if (!signatureDrawing) {

                return;

            }


            const rect =
                signatureCanvas.getBoundingClientRect();


            const scaleX =
                signatureCanvas.width /
                rect.width;


            const scaleY =
                signatureCanvas.height /
                rect.height;


            const x =
                (
                    event.clientX -
                    rect.left
                ) * scaleX;


            const y =
                (
                    event.clientY -
                    rect.top
                ) * scaleY;


            signatureContext.lineTo(
                x,
                y
            );


            signatureContext.stroke();

        }
    );


    signatureCanvas.addEventListener(
        "mouseup",
        function() {

            signatureDrawing =
                false;

        }
    );


    signatureCanvas.addEventListener(
        "mouseleave",
        function() {

            signatureDrawing =
                false;

        }
    );
}


// ==========================================================
// CLEAR SIGNATURE
// ==========================================================

function clearSignature() {

    if (
        !signatureCanvas ||
        !signatureContext
    ) {

        return;

    }


    signatureContext.clearRect(
        0,
        0,
        signatureCanvas.width,
        signatureCanvas.height
    );


    signatureContext.lineWidth =
        2;


    signatureContext.lineCap =
        "round";


    signatureContext.lineJoin =
        "round";


    signatureContext.strokeStyle =
        "#000000";
}


const clearSignatureButton =
    document.getElementById(
        "clearSignature"
    );


if (clearSignatureButton) {

    clearSignatureButton.addEventListener(
        "click",
        clearSignature
    );
}


// ==========================================================
// CLOSE SIGNATURE
// ==========================================================

function closeSignature() {

    if (signatureModal) {

        signatureModal.classList.add(
            "hidden"
        );

    }


    signatureTarget =
        null;
}


const cancelSignature =
    document.getElementById(
        "cancelSignature"
    );


if (cancelSignature) {

    cancelSignature.addEventListener(
        "click",
        closeSignature
    );
}


const closeSignatureButton =
    document.getElementById(
        "closeSignature"
    );


if (closeSignatureButton) {

    closeSignatureButton.addEventListener(
        "click",
        closeSignature
    );
}


// ==========================================================
// APPLY SIGNATURE
// ==========================================================

const applySignature =
    document.getElementById(
        "applySignature"
    );


if (applySignature) {

    applySignature.addEventListener(
        "click",
        function() {

            if (!signatureTarget) {

                return;

            }


            const image =
                signatureCanvas.toDataURL(
                    "image/png"
                );


            const result =
                createElement(
                    signatureTarget.page,
                    "signature",
                    signatureTarget.x,
                    signatureTarget.y
                );


            result.element.classList.add(
                "signature-element"
            );


            result.element.style.width =
                "180px";


            result.element.style.height =
                "70px";


            const img =
                document.createElement(
                    "img"
                );


            img.src =
                image;


            img.draggable =
                false;


            result.element.appendChild(
                img
            );


            result.data.value =
                image;


            result.data.width =
                180;


            result.data.height =
                70;


            result.data.image =
                image;


            closeSignature();


            setStatus(
                "Signature added."
            );

        }
    );
}


// ==========================================================
// SERIALIZE ELEMENTS
// ==========================================================

function serializeElements() {

    return elements.map(
        item => ({

            id:
                item.id,

            type:
                item.type,

            /*
             * ZERO BASED
             */
            page:
                Number(
                    item.page
                ),

            x:
                Number(
                    item.x
                ),

            y:
                Number(
                    item.y
                ),

            width:
                Number(
                    item.width
                ),

            height:
                Number(
                    item.height
                ),

            /*
             * MAIN VALUE
             */
            value:
                item.value || "",

            /*
             * TEXT COMPATIBILITY
             */
            text:
                item.type === "text" ||
                item.type === "date"
                    ? item.value || ""
                    : "",

            /*
             * SIGNATURE COMPATIBILITY
             */
            image:
                item.type === "signature"
                    ? item.value || ""
                    : "",

            fontSize:
                Number(
                    item.fontSize ||
                    (
                        item.type === "date"
                            ? 13
                            : 14
                    )
                ),

            /*
             * Exact PDF dimensions
             */
            pageWidth:
                Number(
                    item.pageWidth || 0
                ),

            pageHeight:
                Number(
                    item.pageHeight || 0
                ),

            scale:
                Number(
                    item.scale || 1
                )

        })
    );
}


// ==========================================================
// FORM SUBMISSION
// ==========================================================

const applicationForm =
    document.getElementById(
        "applicationForm"
    );


if (applicationForm) {

    applicationForm.addEventListener(
        "submit",
        function(event) {

            const data =
                serializeElements();


            const hiddenField =
                document.getElementById(
                    "pdfElements"
                );


            if (!hiddenField) {

                console.error(
                    "pdfElements hidden field not found."
                );

                return;

            }


            hiddenField.value =
                JSON.stringify(
                    data
                );


            console.log(
                "=========================================="
            );


            console.log(
                "PDF ELEMENTS BEING SUBMITTED:"
            );


            console.log(
                JSON.stringify(
                    data,
                    null,
                    2
                )
            );


            console.log(
                "=========================================="
            );


            setStatus(
                "Saving application..."
            );

            /*
             * Do not prevent submission.
             */

        }
    );
}


// ==========================================================
// START
// ==========================================================

clearSignature();

setTool("select");

loadPDF();