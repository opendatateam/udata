describe("Testing datasets page", () => {
  beforeEach(() => {
    cy.visit("/datasets");
    cy.injectAxe();
  });

  it("Displays the page title", () => {
    cy.get("h1").should("be.visible");
  });

  it("Allows you to expand the search options", () => {
    cy.get('a[data-cy="extend-form"]')
      .click()
      .get('[data-cy="extended-form"]')
      .should("be.visible");
  });

  it("Has no detectable critical a11y violations on load", () => {
    cy.checkA11y(null, {
      includedImpacts: ["critical"],
    });
  });
});
