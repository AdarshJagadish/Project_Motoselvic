document.addEventListener('DOMContentLoaded', function () {
    const addressSelect = document.getElementById('address-select');
    const addressDisplay = document.getElementById('address-display');
    const addAddressBtn = document.getElementById('add-address-btn');
    const newAddressForm = document.getElementById('new-address-form');
    const saveAddressBtn = document.getElementById('save-address');
    const totalAmountElem = document.getElementById('total-amount');
    const placeOrderBtn = document.getElementById('place-order-btn');
    const orderSummary = document.getElementById('order-summary');
    
    let cartItems = [];
    {% for item in cart_items %}
        cartItems.push({
            name: "{{ item.product.name }}",
            price: {{ item.product.price }},
            quantity: {{ item.quantity }},
            image: "{{ item.product.main_image.url }}"
        });
    {% endfor %}

    // Calculate total
    function calculateTotal() {
        let total = 0;
        cartItems.forEach(item => {
            total += item.price * item.quantity;
        });
        totalAmountElem.textContent = total;
    }

    // Show/hide new address form
    addAddressBtn.addEventListener('click', function () {
        newAddressForm.style.display = (newAddressForm.style.display === 'none' || newAddressForm.style.display === '') ? 'block' : 'none';
    });

    // Show address details on selection
    addressSelect.addEventListener('change', function () {
        const selected = this.options[this.selectedIndex];
        if (selected.dataset.addressLine) {
            document.getElementById('display-address-line').textContent = selected.dataset.addressLine;
            document.getElementById('display-city').textContent = selected.dataset.city;
            document.getElementById('display-state').textContent = selected.dataset.state;
            document.getElementById('display-postal-code').textContent = selected.dataset.postalCode;
            document.getElementById('display-country').textContent = selected.dataset.country;
            addressDisplay.style.display = 'block';
        } else {
            addressDisplay.style.display = 'none';
        }
    });

    // Save new address logic (you'd probably need to handle this server-side via Django form submission)
    saveAddressBtn.addEventListener('click', function () {
        // Add your save logic here
        alert("New address saved!");
        newAddressForm.style.display = 'none';
    });

    // Place Order Button functionality
    placeOrderBtn.addEventListener('click', function () {
        // Add order submission logic here (make a POST request to submit the order)
        alert("Order placed!");
    });

    calculateTotal();
});
