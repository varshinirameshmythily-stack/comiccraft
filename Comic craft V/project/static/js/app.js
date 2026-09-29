function showGeneratingState(form) {
    const overlay = document.getElementById("loading-panel");
    if (!overlay) return;

    overlay.classList.add("active");
    overlay.setAttribute("aria-hidden", "false");

    const button = form?.querySelector("button[type='submit']");
    if (button) {
        button.disabled = true;
        button.querySelector("span")?.replaceChildren(document.createTextNode("Generating Comic..."));
    }
}

function downloadComic(pdfPath, button) {
    if (button) {
        button.disabled = true;
        button.textContent = "Preparing PDF...";
    }

    fetch(pdfPath)
        .then(response => {
            if (!response.ok) throw new Error("PDF download failed.");
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = pdfPath.split("/").pop() || "comic.pdf";
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);

            const filename = pdfPath.split("/").pop() || "comic.pdf";
            window.location.href = `/export-success?filename=${encodeURIComponent(filename)}`;
        })
        .catch(error => {
            alert(error.message);
            if (button) {
                button.disabled = false;
                button.textContent = "📄 Download Your Comic as PDF";
            }
        });
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("comic-form");
    if (form) {
        form.addEventListener("submit", () => showGeneratingState(form));
    }
});
