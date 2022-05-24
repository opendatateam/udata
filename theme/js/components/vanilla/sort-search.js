export default (() => {
    document.addEventListener("DOMContentLoaded", () => {
        /**
         * @type {NodeListOf<HTMLSelectElement>}
         */
        const selects = document.querySelectorAll("[data-select-sort]");

        selects.forEach((select) => {
            const options = select.querySelectorAll("option");

            options.forEach((option) => {
                option.disabled = false;
            });
            if(select.form) {
                select.addEventListener('change', e => {
                    select.form?.dispatchEvent(new Event('submit'));
                });
                select.form.addEventListener('submit', e => {
                    e.preventDefault();
                    if(!select.value) {
                        select.disabled = true;
                    }
                    select.form?.submit();
                });
            }
        });
    });
})();