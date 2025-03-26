function confirmRemove(paymentId) {
    let confirmAction = confirm("Are you sure you want to remove this payment method?");
    if (confirmAction) {
        alert("Payment method removed successfully!");
        document.getElementById("payment-" + paymentId).style.display = "none";
    }
}

function addPaymentMethod() {
    let paymentType = prompt("Enter payment method (e.g., Visa **** 5678 or UPI: yourupi@bank):");
    if (paymentType) {
        let paymentList = document.getElementById("payment-list");
        let newPayment = document.createElement("p");
        let paymentId = Date.now(); // Unique ID for new payment method
        newPayment.id = "payment-" + paymentId;
        newPayment.innerHTML = `${paymentType} <button class='btn btn-sm btn-outline-danger' onclick='confirmRemove("${paymentId}")'>Remove</button>`;
        paymentList.appendChild(newPayment);
        alert("Payment method added successfully!");
    }
}
