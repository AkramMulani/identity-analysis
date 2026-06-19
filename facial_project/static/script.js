document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    var loadingDiv = document.getElementById('loading');
    if (loadingDiv) loadingDiv.style.display = 'block';
    let resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '';
    const formData = new FormData();
    formData.append('image', document.getElementById('photo').files[0]);
    try {
        const response = await fetch('/compare', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (result.message) {
            resultDiv.innerHTML += `<div class='mb-3 fw-bold'>${result.message}</div>`;
        }
        // Show match details if found
        if (result.faces && result.faces.length > 0) {
            let anyMatch = false;
            result.faces.forEach(face => {
                if (face.matches && face.matches.length > 0) {
                    anyMatch = true;
                    face.matches.forEach(match => {
                        resultDiv.innerHTML += `
                            <div class="card forensic-result-card mb-3">

                                <div class="card-body">

                                    <div class="d-flex justify-content-between">

                                        <h5 class="text-success">
                                            Match Found
                                        </h5>

                                        <span class="badge bg-success">
                                            VERIFIED
                                        </span>

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
                    });
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