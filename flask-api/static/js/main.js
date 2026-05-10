const deleteButtons = document.querySelectorAll(".btn-delete");

deleteButtons.forEach((button) => {
  button.addEventListener("click", (event) => {
    const confirmed = confirm("¿Seguro que deseas eliminar este producto?");

    if (!confirmed) {
      event.preventDefault();
    }
  });
});
