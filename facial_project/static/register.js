// register.js

document.addEventListener('DOMContentLoaded', function() {
    const cameraButton = document.getElementById('personPhotoCameraBtn');
    const cameraInput = document.getElementById('personPhotoCamera');
    const cameraLabel = document.getElementById('personPhotoCameraLabel');
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

document.getElementById('addPersonForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    document.getElementById('addPersonLoading').style.display = 'block';
    document.getElementById('addPersonResult').innerText = '';
    const formData = new FormData();
    formData.append('name', document.getElementById('personName').value);
    formData.append('age', document.getElementById('personAge').value);
    formData.append('gender', document.getElementById('personGender').value);
    formData.append('address', document.getElementById('personAddress').value);

    const cameraFile = document.getElementById('personPhotoCamera').files[0];
    const storageFile = document.getElementById('personPhotoStorage').files[0];
    if (cameraFile) {
        formData.append('camera_image', cameraFile);
    }
    if (storageFile) {
        formData.append('image', storageFile);
    }

    if (!cameraFile && !storageFile) {
        document.getElementById('addPersonResult').innerText = 'Please capture a photo or choose one from storage.';
        document.getElementById('addPersonLoading').style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/add_person', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (result.error) {
            document.getElementById('addPersonResult').innerText = result.error;
        } else {
            document.getElementById('addPersonResult').innerText = 'Person registered successfully!';
        }
    } catch (err) {
        document.getElementById('addPersonResult').innerText = 'Error registering person.';
    }
    document.getElementById('addPersonLoading').style.display = 'none';
});
