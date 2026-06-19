// register.js

document.getElementById('addPersonForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    document.getElementById('addPersonLoading').style.display = 'block';
    document.getElementById('addPersonResult').innerText = '';
    const formData = new FormData();
    formData.append('name', document.getElementById('personName').value);
    formData.append('age', document.getElementById('personAge').value);
    formData.append('gender', document.getElementById('personGender').value);
    formData.append('address', document.getElementById('personAddress').value);
    formData.append('image', document.getElementById('personPhoto').files[0]);
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
