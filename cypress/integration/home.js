describe("Testing home page", () => {
  beforeEach(() => {
    cy.visit("/");
    cy.injectAxe();
  });

  it("Displays the home page title", () => {
    cy.get("h1").should("be.visible");
  });

  it("Allows you to search (suggest) for datasets and reuses and correctly displays 'empty results' state", () => {
    cy.get('input[name="q"]')
      .focus()
      .get('input[data-cy="search-input"]')
      .should("be.visible")
      .type("🐎")
      .get(".search-empty")
      .contains("🐎");
  });

  it("Has no detectable critical a11y violations on load", () => {
    cy.checkA11y(null, {
      includedImpacts: ["critical"],
    });
  });
});
