jQuery(document).ready(function() {
//
// NOTE: 
// Modifying the URL below to another server will likely *NOT* work. Because of browser
// security restrictions, we have to use a file server with special headers
// (CORS) - most servers don't support cross-origin browser requests.
//
var url = document.getElementById('pdf_file').value;

//
// Disable workers to avoid yet another cross-origin issue (workers need the URL of
// the script to be loaded, and currently do not allow cross-origin scripts)
//
PDFJS.disableWorker = true;

var pdfDoc = null,
    pageNum = 1,
    pageRendering = false,
    pageNumPending = null,
    scale = 1,
    canvas = document.getElementById('pdfcanvas'),
    ctx = canvas.getContext('2d');
    

/**
 * Get page info from document, resize canvas accordingly, and render page.
 * @param num Page number.
 */
function renderPage(num) {
  pageRendering = true;
  // Using promise to fetch the page
  pdfDoc.getPage(num).then(function(page) {
    var viewport = page.getViewport(scale);
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    // Render PDF page into canvas context
    var renderContext = {
      canvasContext: ctx,
      viewport: viewport
    };
    var renderTask = page.render(renderContext);  
    
    // Wait for rendering to finish
    renderTask.promise.then(function () {
      pageRendering = false;
      if (pageNumPending !== null) {
        // New page rendering is pending
        renderPage(pageNumPending);
        pageNumPending = null;
      }
    });
  });

  // Update page counters
  document.getElementById('page_num').textContent = pageNum;
}

/**
 * If another page rendering in progress, waits until the rendering is
 * finised. Otherwise, executes rendering immediately.
 */
function queueRenderPage(num) {
  if (pageRendering) {
    pageNumPending = num;
  } else {
    renderPage(num);
  }
}

/**
 * Displays previous page.
 */
function onPrevPage() {
  if (pageNum <= 1) {
    return;
  }
  pageNum--;
  queueRenderPage(pageNum);
}
document.getElementById('prev').addEventListener('click', onPrevPage);

/**
 * Displays next page.
 */
function onNextPage() {
  if (pageNum >= pdfDoc.numPages) {
    return;
  }
  pageNum++;
  queueRenderPage(pageNum);
}
document.getElementById('next').addEventListener('click', onNextPage);

/**
 * Displays last page.
 */
function onLastPage() {  
  pageNum = pdfDoc.numPages;
  queueRenderPage(pdfDoc.numPages);
}
document.getElementById('lastpage').addEventListener('click', onLastPage);

/**
 * Displays first page.
 */
function onFirstPage() {  
  pageNum = 1;
  queueRenderPage(1);
}
document.getElementById('firstpage').addEventListener('click', onFirstPage);

document.addEventListener('keydown', function(e) {
  if(e.keyCode==37){
    onPrevPage();
  }
  if(e.keyCode==39){
    onNextPage();
  }
});

/**
 * Asynchronously downloads PDF.
 */
PDFJS.getDocument(url).then(function (pdfDoc_) {
  pdfDoc = pdfDoc_;
  document.getElementById('page_count').textContent = pdfDoc.numPages;

  // Initial/first page rendering
  renderPage(pageNum);
});


function goFullscreen() {
  // Get the element that we want to take into fullscreen mode
  var element = document.getElementById('pdfcanvas');
  
  // These function will not exist in the browsers that don't support fullscreen mode yet, 
  // so we'll have to check to see if they're available before calling them.
  
  if (element.mozRequestFullScreen) {
    // This is how to go into fullscren mode in Firefox
    // Note the "moz" prefix, which is short for Mozilla.
    element.mozRequestFullScreen();
  } else if (element.webkitRequestFullScreen) {
    // This is how to go into fullscreen mode in Chrome and Safari
    // Both of those browsers are based on the Webkit project, hence the same prefix.
    element.webkitRequestFullScreen();
  }
 // Hooray, now we're in fullscreen mode!
}
document.getElementById('fullscreen').addEventListener('click', goFullscreen);

}); //end document.ready 