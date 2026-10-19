document.addEventListener('DOMContentLoaded', function () {
    // Мобильное меню
    var toggle = document.getElementById('nav-toggle');
    var links = document.getElementById('nav-links');
    if (toggle && links) {
        toggle.addEventListener('click', function () {
            links.classList.toggle('active');
        });
    }

    // Показ имени выбранного файла аватарки
    var fileInput = document.getElementById('avatar-file-input');
    var fileName = document.getElementById('avatar-file-name');
    if (fileInput && fileName) {
        fileInput.addEventListener('change', function () {
            fileName.textContent = fileInput.files.length > 0 ? fileInput.files[0].name : 'Файл не выбран';
        });
    }
});
