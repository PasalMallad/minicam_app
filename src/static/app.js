// src/static/app.js


// ============================================================
// DIODE MAP
// ============================================================

const diodeMap = [
    [24, 19, 14,  10,  5],
    [23, 18, 13,  9,  4],
    [22, 17, null,  8,  3],
    [21, 16, 12,  7,  2],
    [20, 15, 11, 6,  1]
];


// ============================================================
// ELEMENTS
// ============================================================

const scanButton =
    document.getElementById(
        "scanButton"
    );

const streamButton =
    document.getElementById(
        "streamButton"
    );

const stopButton =
    document.getElementById(
        "stopButton"
    );

const status =
    document.getElementById(
        "status"
    );

const cameraImage =
    document.getElementById(
        "cameraImage"
    );

const grid =
    document.getElementById(
        "grid"
    );


// ============================================================
// GRID
// ============================================================

function getGrayscaleStyle(val, min = 0, max = 4095) {
    // Normalizar entre 0 y 1
    const normalized = Math.min(Math.max((val - min) / (max - min), 0), 1);

    // Relación directa:
    // val cercano a 0 (oscuridad)  -> brightness = 0 (Negro)
    // val cercano a max (mucha luz) -> brightness = 255 (Blanco)
    const brightness = Math.round(normalized * 255);

    // Contraste automático para que las letras nunca se pierdan:
    // Fondo oscuro (brightness <= 128) -> texto blanco
    // Fondo claro (brightness > 128)  -> texto negro
    const isDark = brightness <= 128;

    return {
        backgroundColor: `rgb(${brightness}, ${brightness}, ${brightness})`,
        textColor: isDark ? "#ffffff" : "#000000",
        subtextColor: isDark ? "#b0b0b0" : "#555555"
    };
}


function createGrid(values) {
    if (!values) {
        return;
    }

    grid.innerHTML = "";

    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const diode = diodeMap[row][col];
            const cell = document.createElement("div");

            if (diode === null) {
                cell.className = "cell empty";
                grid.appendChild(cell);
                continue;
            }

            cell.className = "cell";

            const diodeVal = values[diode - 1];
            const style = getGrayscaleStyle(diodeVal, 0, 4095);

            // Fondo según nivel de luz
            cell.style.backgroundColor = style.backgroundColor;

            // Etiqueta del fotodiodo (D1, D2...)
            const number = document.createElement("div");
            number.className = "number";
            number.textContent = `D${diode}`;
            number.style.color = style.subtextColor;

            // Valor medido por el ADC
            const value = document.createElement("div");
            value.className = "value";
            value.textContent = diodeVal;
            value.style.color = style.textColor;

            cell.appendChild(number);
            cell.appendChild(value);

            grid.appendChild(cell);
        }
    }
}

// ============================================================
// PHOTO + SCAN
// ============================================================

async function performScan() {

    scanButton.disabled = true;

    streamButton.disabled = true;

    status.textContent =
        "Taking photo and scanning...";


    try {

        const response =
            await fetch(
                "/api/scan",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.error
            );
        }


        // Update image

        cameraImage.src =
            data.image +
            "?t=" +
            Date.now();


        // Update grid

        createGrid(
            data.values
        );


        status.textContent =
            "Scan completed";


    } catch (error) {

        console.error(
            error
        );

        status.textContent =
            "Error: " +
            error.message;

    } finally {

        scanButton.disabled =
            false;

        streamButton.disabled =
            false;
    }
}


// ============================================================
// START STREAM
// ============================================================

async function startStream() {

    streamButton.disabled =
        true;

    scanButton.disabled =
        true;

    stopButton.disabled =
        false;

    status.textContent =
        "Starting constant stream...";


    try {

        const response =
            await fetch(
                "/api/stream/start",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.message
            );
        }


        status.textContent =
            "Constant stream running";

        pollStream();


    } catch (error) {

        console.error(
            error
        );

        status.textContent =
            "Error: " +
            error.message;


        streamButton.disabled =
            false;

        scanButton.disabled =
            false;

        stopButton.disabled =
            true;
    }
}


// ============================================================
// POLL STREAM
// ============================================================

async function pollStream() {

    try {

        const response =
            await fetch(
                "/api/stream/data"
            );


        const data =
            await response.json();


        // --------------------------------------------
        // New image
        // --------------------------------------------

        if (data.image) {

            cameraImage.src =
                "data:image/jpeg;base64," +
                data.image;
        }


        // --------------------------------------------
        // New ADC values
        // --------------------------------------------

        if (data.values) {

            createGrid(
                data.values
            );
        }


        // --------------------------------------------
        // Continue polling
        // --------------------------------------------

        if (data.running) {

            setTimeout(
                pollStream,
                50
            );

        } else {

            streamStopped();
        }


    } catch (error) {

        console.error(
            "Stream error:",
            error
        );

        status.textContent =
            "Stream error";

        streamStopped();
    }
}


// ============================================================
// STOP STREAM
// ============================================================

async function stopStream() {

    stopButton.disabled =
        true;


    try {

        await fetch(
            "/api/stream/stop",
            {
                method: "POST"
            }
        );

    } catch (error) {

        console.error(
            error
        );
    }
}


// ============================================================
// STREAM STOPPED
// ============================================================

function streamStopped() {

    streamButton.disabled =
        false;

    scanButton.disabled =
        false;

    stopButton.disabled =
        true;

    status.textContent =
        "Stream stopped";
}


// ============================================================
// BUTTONS
// ============================================================

scanButton.addEventListener(
    "click",
    performScan
);

streamButton.addEventListener(
    "click",
    startStream
);

stopButton.addEventListener(
    "click",
    stopStream
);

(() => {
    const burstButton = document.getElementById("burstButton");
    const status = document.getElementById("status");
    const results = document.getElementById("burstResults");
    const cameraImage = document.getElementById("cameraImage");
    const scanButton = document.getElementById("scanButton");
    const streamButton = document.getElementById("streamButton");
    const stopButton = document.getElementById("stopButton");

    if (!burstButton || !status || !results) {
        return;
    }

    function addLink(parent, url, label) {
        if (!url) return;

        const link = document.createElement("a");
        link.href = url;
        link.textContent = label;
        link.target = "_blank";
        link.rel = "noopener";
        parent.appendChild(link);
    }

    burstButton.addEventListener("click", async () => {
        if (stopButton && !stopButton.disabled) {
            status.textContent = "Detén el stream constante antes de iniciar la ráfaga.";
            return;
        }

        results.replaceChildren();
        status.textContent = "Capturando ráfaga… Puede tardar unos 30 segundos.";

        const controls = [burstButton, scanButton, streamButton].filter(Boolean);
        const previousDisabledStates = controls.map(button => button.disabled);
        controls.forEach(button => {
            button.disabled = true;
        });

        try {
            const response = await fetch("/api/burst", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    duration: 30,
                    fps: 2,
                }),
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || `Error HTTP ${response.status}`);
            }

            status.textContent = `Ráfaga completada: ${data.frames_saved} frames guardados.`;

            addLink(results, data.csv, "Descargar CSV");
            addLink(results, data.json, "Descargar JSON");
            addLink(results, data.video, "Abrir video MP4");

            if (data.video_warning) {
                const warning = document.createElement("p");
                warning.className = "burst-warning";
                warning.textContent = data.video_warning;
                results.appendChild(warning);
            }

            if (data.images && data.images.length > 0) {
                const details = document.createElement("details");
                details.className = "burst-images";

                const summary = document.createElement("summary");
                summary.textContent = `Imágenes JPEG (${data.images.length})`;
                details.appendChild(summary);

                data.images.forEach((url, index) => {
                    addLink(details, url, `Frame ${index + 1}`);
                });

                results.appendChild(details);

                if (cameraImage) {
                    cameraImage.src = `${data.images[data.images.length - 1]}?t=${Date.now()}`;
                }
            }
        } catch (error) {
            status.textContent = `Error en la ráfaga: ${error.message}`;
        } finally {
            controls.forEach((button, index) => {
                button.disabled = previousDisabledStates[index];
            });
        }
    });
})();