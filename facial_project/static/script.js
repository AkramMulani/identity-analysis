document.addEventListener('DOMContentLoaded', function() {
    const cameraButton = document.getElementById('photoCameraBtn');
    const cameraInput = document.getElementById('photoCamera');
    const cameraLabel = document.getElementById('photoCameraLabel');
    const modal = document.getElementById('cameraModal');
    const video = document.getElementById('cameraVideo');
    const captureBtn = document.getElementById('cameraCaptureBtn');
    const cancelBtn = document.getElementById('cameraCancelBtn');
    const closeBtn = document.getElementById('cameraCloseBtn');
    let stream = null;

    function stopStream() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
    }

    function hideModal() {
        stopStream();
        if (modal) {
            modal.classList.add('d-none');
        }
    }

    if (cameraButton && cameraInput) {
        cameraButton.addEventListener('click', async function() {
            try {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    cameraInput.click();
                    return;
                }
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
                if (video) {
                    video.srcObject = stream;
                }
                if (modal) {
                    modal.classList.remove('d-none');
                }
            } catch (err) {
                cameraInput.click();
            }
        });

        if (captureBtn) {
            captureBtn.addEventListener('click', function() {
                const canvas = document.createElement('canvas');
                canvas.width = video && video.videoWidth ? video.videoWidth : 640;
                canvas.height = video && video.videoHeight ? video.videoHeight : 480;
                const context = canvas.getContext('2d');
                if (video) {
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                }
                canvas.toBlob(function(blob) {
                    if (!blob) {
                        hideModal();
                        return;
                    }
                    const file = new File([blob], 'captured-image.jpg', { type: 'image/jpeg' });
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    cameraInput.files = dataTransfer.files;
                    if (cameraLabel) {
                        cameraLabel.textContent = file.name;
                    }
                    hideModal();
                }, 'image/jpeg');
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', hideModal);
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', hideModal);
        }

        cameraInput.addEventListener('change', function() {
            if (cameraLabel) {
                cameraLabel.textContent = cameraInput.files && cameraInput.files[0] ? cameraInput.files[0].name : 'No image selected';
            }
        });
    }
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    var loadingDiv = document.getElementById('loading');
    if (loadingDiv) loadingDiv.style.display = 'block';
    let resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '';
    const formData = new FormData();
    const cameraFile = document.getElementById('photoCamera').files[0];
    const storageFile = document.getElementById('photoStorage').files[0];

    if (cameraFile) {
        formData.append('camera_image', cameraFile);
    }
    if (storageFile) {
        formData.append('image', storageFile);
    }

    if (!cameraFile && !storageFile) {
        resultDiv.innerHTML = '<div class="text-danger">Please capture a photo or choose one from storage.</div>';
        if (loadingDiv) loadingDiv.style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/compare', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (result.message) {
            resultDiv.innerHTML += `<div class='mb-3 fw-bold'>${result.message}</div>`;
        }
        if (result.faces && result.faces.length > 0) {
            let anyMatch = false;
            result.faces.forEach(face => {
                if (face.matches && face.matches.length > 0) {
                    anyMatch = true;
                    const match = face.matches[0];
                    resultDiv.innerHTML += `
                        <div class="card forensic-result-card mb-3">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <h5 class="text-success">Best Match</h5>
                                    <span class="badge bg-success">VERIFIED</span>
                                </div>
                                <hr>
                                <div class="row g-3 align-items-center">
                                    <div class="col-md-4">
                                        <div class="ratio ratio-1x1 rounded-3 overflow-hidden bg-dark">
                                            ${match.photo_url ? `<img src="${match.photo_url}" alt="${match.name || 'Matched person'}" class="w-100 h-100 object-fit-cover">` : `<div class="d-flex align-items-center justify-content-center text-light small">No photo available</div>`}
                                        </div>
                                    </div>
                                    <div class="col-md-8">
                                        <p><b>Name:</b> ${match.name}</p>
                                        <p><b>Person ID:</b> ${match.person_id}</p>
                                        <p><b>Age:</b> ${match.age || 'N/A'}</p>
                                        <p><b>Gender:</b> ${match.gender || 'N/A'}</p>
                                        <p class="mb-0"><b>Address:</b> ${match.address || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            if (!anyMatch) {
                resultDiv.innerHTML += `<div class='text-danger'>No similar faces found.</div>`;
            }
        }
        else {
            resultDiv.innerHTML += `<div class='text-danger'>No faces detected.</div>`;
        }
    } catch (err) {
        resultDiv.innerHTML = '<div class="text-danger">Error processing request.</div>';
    }
    if (loadingDiv) loadingDiv.style.display = 'none';
});