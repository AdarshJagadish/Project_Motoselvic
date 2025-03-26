document.addEventListener("DOMContentLoaded", function() {
    let orderStatus = "Completed"; // Change to "Pending" for testing
    let orderActions = document.getElementById("order-actions");
    
    if (orderStatus === "Pending") {
        let cancelButton = document.createElement("button");
        cancelButton.className = "btn btn-danger";
        cancelButton.innerText = "Cancel Order";
        cancelButton.onclick = function() {
            if (confirm("Are you sure you want to cancel this order?")) {
                alert("Order has been cancelled.");
                document.getElementById("order-status").innerHTML = "<span class='badge bg-danger'>Cancelled</span>";
                orderActions.innerHTML = "";
            }
        };
        orderActions.appendChild(cancelButton);
    } else if (orderStatus === "Completed") {
        let returnButton = document.createElement("button");
        returnButton.className = "btn btn-warning me-2";
        returnButton.innerText = "Return/Replace";
        
        let orderAgainButton = document.createElement("button");
        orderAgainButton.className = "btn btn-primary";
        orderAgainButton.innerText = "Order Again";
        
        orderActions.appendChild(returnButton);
        orderActions.appendChild(orderAgainButton);
    }
});
