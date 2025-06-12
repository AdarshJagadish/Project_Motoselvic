document.addEventListener('DOMContentLoaded', function () {
    const categorySelect = document.getElementById('category');
    const searchButton = document.querySelector('.search-bar button');
    const searchInput = document.querySelector('.search-bar input');

    if (searchButton && searchInput) {
        searchButton.addEventListener('click', function () {
            const category = categorySelect ? categorySelect.value : '';
            const searchQuery = searchInput.value;

            console.log('Category:', category);
            console.log('Search Query:', searchQuery);
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', function () {
            const selectedCategory = categorySelect.value;
            console.log('Selected Category:', selectedCategory);
        });
    }
});
