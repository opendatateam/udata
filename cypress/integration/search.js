describe("Testing search bar", () => {
  beforeEach(() => {
    cy.visit("/");
    cy.injectAxe();
    const input = 'input[data-cy="search-input"]';
    cy.get(input).as('input');
    cy.get('@input').invoke('attr', 'aria-controls').then(val => {
      cy.get("#" + val).as('popup');
    });
  });
  it("Show you a search bar", () => {
    cy.get('@input').should("be.visible");
  });

  it("Open popup as you type", () => {
    cy.get('@input')
      .type("some string")
      .get('@popup')
      .should("be.visible");
  });

  it("Focus an empty field don't open the popup", () => {
    cy.get('@input')
      .focus()
      .get('@popup')
      .should("be.hidden");
  });
  it("Focus out should close the popup", () => {
    cy.get('@input')
      .type("some string")
      .get('a')
      .first()
      .focus()
      .get('@popup')
      .should("be.hidden");
  });
  it("Popup content should contain typed string", () => {
    const typed = "some string";
    cy.get('@input')
      .type(typed)
      .invoke('attr', 'aria-activedescendant').then(val => {
        cy.get("#" + val).should(($option) => {
          expect($option).to.contain(typed);
        });
      });
  });
  it("Click on first option should change to datasets page", () => {
    const typed = "somestring";
    cy.get('@input')
      .type(typed)
      .invoke('attr', 'aria-activedescendant').then(val => {
        cy.get("#" + val).click().then(() => {
          cy.url().should('include', 'datasets');
          cy.url().should('include', typed);
        });
      });
  });
});
