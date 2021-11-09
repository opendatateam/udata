export const PAGES_AROUND = 3;

function range(size, startAt = 1) {
  return [...Array(size).keys()].map((i) => i + startAt);
}

function getPages(pageCount) {
  return range(pageCount);
}

function getPagesShown(pages, currentPage) {
  return Math.min(
    PAGES_AROUND * 2 + 1, // we want 3 pages around the current one, this is the default
    pages.length - 2, // we want to show at most all pages except the first and last
    PAGES_AROUND + currentPage - 1, // if we're close to the first page, we'll show less than 3 pages on the left
    PAGES_AROUND + pages.length - currentPage // if we're close to the last page, we'll show less than 3 pages on the right
  );
}

function getStartPage(currentPage) {
  return Math.max(
    currentPage - PAGES_AROUND, // we want to start 3 pages before the current one
    2 // we don't want to start below page 2
  )
}

export default function getVisiblePages(currentPage, pageCount) {
  const pages = getPages(pageCount);
  const start = getStartPage(currentPage);
  if (pageCount <= 2) {
     return [];
  }
  let pagination = range(getPagesShown(pages, currentPage), start);
  if(!pagination.includes(2)) {
    pagination.unshift(null);
  }
  if(!pagination.includes(pageCount - 1)) {
    pagination.push(null);
  }
  return pagination;
}
