import getVisiblePages, {PAGES_AROUND} from "/theme/js/components/vanilla/pagination";

const PAGE_COUNT_WITHOUT_ELLIPSIS = 5;
const PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE = 6;
const PAGE_COUNT_WITH_ELLIPSIS_ON_BOTH_SIDES = 11;

describe('Pagination Unit Test', function () {
  context('getVisiblePages', function () {
    it('returns an empty array when page count is <= 2', function () {
      expect(getVisiblePages(0, 0)).to.be.an('array').that.is.empty;
      expect(getVisiblePages(0, 1)).to.be.an('array').that.is.empty;
      expect(getVisiblePages(0, 2)).to.be.an('array').that.is.empty;
    })

    it('returns [2, 3, 4] on first page', function () {
      expect(getVisiblePages(PAGE_COUNT_WITHOUT_ELLIPSIS - PAGES_AROUND - 1, PAGE_COUNT_WITHOUT_ELLIPSIS)).to.deep.equal([2, 3, 4]);
    })

    it('returns [2, 3, 4] on last page', function () {
      expect(getVisiblePages(PAGE_COUNT_WITHOUT_ELLIPSIS, PAGE_COUNT_WITHOUT_ELLIPSIS)).to.deep.equal([2, 3, 4]);
    })
    it('add null if page 2 is not in array', function () {
      const pagination = getVisiblePages(PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE, PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE);
      expect(pagination).to.be.an('array').that.include(null);
      expect(pagination).to.be.an('array').that.does.not.include(2);
    })
    it('add null if the second last page is not in array', function () {
      const pagination = getVisiblePages(1, PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE);
      expect(pagination).to.be.an('array').that.include(null);
      expect(pagination).to.be.an('array').that.does.not.include(PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE - 1);
    })
    it('add null on both sides if page 2 and the second last page are not in array', function () {
      const pagination = getVisiblePages(6, PAGE_COUNT_WITH_ELLIPSIS_ON_BOTH_SIDES);
      expect(pagination).to.be.an('array').that.include(null);
      expect(pagination).to.be.an('array').that.does.not.include(2);
      expect(pagination).to.be.an('array').that.does.not.include(PAGE_COUNT_WITH_ELLIPSIS_ON_BOTH_SIDES - 1);
      expect(pagination).to.be.an('array').that.have.lengthOf(PAGES_AROUND * 2 + 3);
    })
    it('never contain pages greater than the last one', function () {
      const pagination = getVisiblePages(PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE, PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE);
      expect(pagination).to.be.an('array').that.satisfy(pages =>
        pages.every(page => page < PAGE_COUNT_WITH_ELLIPSIS_ON_ONE_SIDE)
      );
    })
  })
})
