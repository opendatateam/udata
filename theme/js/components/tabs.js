document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".tabs");

  //For each .tabs container
  tabs.forEach((tab) => {
    //Tabs buttons = pills button
    const tabsButtons = tab.querySelectorAll(".tab[href^='#']");

    tabsButtons.forEach((tabButton) => {
      tabButton.addEventListener("click", (el) => {
        el.preventDefault();

        //Find the previously active pill button
        const previouslyActive = Array.from(tabsButtons).find((tab) =>
          tab.classList.contains("active")
        );

        //Remove the "active" class from the previously active tabPane and pill button
        if (previouslyActive) {
          previouslyActive.classList.remove("active");
          document
            .querySelector(previouslyActive.getAttribute("href"))
            .classList.remove("active");
        }

        //Add active to new pill and tab pane
        el.target.classList.add("active");
        document
          .querySelector(el.target.getAttribute("href"))
          .classList.add("active");
      });
    });
  });
});
