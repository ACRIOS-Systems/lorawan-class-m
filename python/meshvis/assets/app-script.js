var appInitialized = false;
var isMouseDown = false;

function disableTransitions() {
    document.getElementById('app-window-top-left').classList.add('no-transition');
    document.getElementById('app-window-top-right').classList.add('no-transition');
    document.getElementById('app-window-bottom').classList.add('no-transition');
}

function enableTransitions() {
    document.getElementById('app-window-top-left').classList.remove('no-transition');
    document.getElementById('app-window-top-right').classList.remove('no-transition');
    document.getElementById('app-window-bottom').classList.remove('no-transition');
}

function onDragCallback() {
    // Prepared if needed in the future
}

function newButton(id, name, imgName) {
    img = document.createElement("img");
    img.setAttribute("src", "assets/images/" + imgName);
    img.classList.add('modebar-img');

    btn = document.createElement("a");
    btn.appendChild(img);
    btn.classList.add('modebar-btn');
    btn.setAttribute('id', id);
    btn.setAttribute('data-title', name);

    return btn;
}


function isSubChildOf(element, plotName) {
    parent = element.parentElement
    while (parent != null) {
        if (parent.id == plotName) {
            return true;
        }
        parent = parent.parentElement
    }
    return false;
}


async function appInit() {
    // Sometimes the function executed twice
    if (appInitialized == true) return;
    appInitialized = true;

    while (document.getElementById("app-window-top-right") == null)
        await new Promise(r => setTimeout(r, 1));


    var splitLeftRight = Split(['#app-window-top-left', '#app-window-top-right'], {
        sizes: [50, 50], // Initial sizes of the split areas
        minSize: [0, 0],
        snapOffset: 100,
        gutterSize: 4, // Size of the gutter (space between split areas)
        direction: 'horizontal', // Split direction
        onDragStart: disableTransitions,
        onDragEnd: enableTransitions,
        onDrag: onDragCallback
    });

    var splitTopBot = Split(['#app-window-top', '#app-window-bottom'], {
        sizes: [66, 34], // Initial sizes of the split areas
        minSize: [0, 0],
        snapOffset: 100,
        gutterSize: 4, // Size of the gutter (space between split areas)
        direction: 'vertical', // Split direction
        onDragStart: disableTransitions,
        onDragEnd: enableTransitions,
        onDrag: onDragCallback
    });

    // Set app-menu-content frame's max-width dynamically
    document.getElementById("app-menu-content").style.maxWidth = document.getElementById("app-menu-content").offsetWidth + "px";

    // On menu show click
    document.getElementById('app-menu-button').onclick = function() {
        document.getElementById('app-menu-content').classList.toggle('hidden');
        document.getElementById('app-menu-button').classList.toggle('hidden');
        //splitLeftRight.collapse(0);
    }

    // Detect when the mouse is pressed to prevent plots from updating
    document.addEventListener('mousedown', function(event) {
        isMouseDown = true;
    }, true);


    document.addEventListener('mouseup', function(event) {
        isMouseDown = false;
    }, true);


    // Wait until all modebars get loaded
    while (document.getElementsByClassName('modebar-container').length < 3)
        await new Promise(r => setTimeout(r, 10));
    await new Promise(r => setTimeout(r, 10));

    // Functions for custom buttons
    function maximizeTL() {
        splitTopBot.collapse(1);
        splitLeftRight.collapse(1);
    }

    function maximizeTR() {
        splitTopBot.collapse(1);
        splitLeftRight.collapse(0);
    }

    function maximizeB() {
        splitTopBot.collapse(0);
    }

    function minimizeTL() {
        splitLeftRight.collapse(0);
    }

    function minimizeTR() {
        splitLeftRight.collapse(1);
    }

    function minimizeB() {
        splitTopBot.collapse(1);
    }

    //DEBUG
    //return;

    // Add custom buttons
    modebars = document.getElementsByClassName('modebar-container');
    for (var i = (modebars.length - 1); i >= 0; i--) {
        if (isSubChildOf(modebars[i], "app-window-top-right")) {
            groupDiv = document.createElement("div");
            groupDiv.classList.add('modebar-group');
            modebars[i].firstChild.appendChild(groupDiv);

            btn = newButton('maximizeBtn-TR', 'Maximize', 'expand.svg');
            groupDiv.appendChild(btn);
            btn.onclick = maximizeTR;

            btn = newButton('minimizeBtn-TR', 'Minimize', 'collapse.svg');
            groupDiv.appendChild(btn);
            btn.onclick = minimizeTR;
        } else if (isSubChildOf(modebars[i], "app-window-top-left")) {
            groupDiv = document.createElement("div");
            groupDiv.classList.add('modebar-group');
            modebars[i].firstChild.appendChild(groupDiv);

            btn = newButton('maximizeBtn-TL', 'Maximize', 'expand.svg');
            groupDiv.appendChild(btn);
            btn.onclick = maximizeTL;

            btn = newButton('minimizeBtn-TL', 'Minimize', 'collapse.svg');
            groupDiv.appendChild(btn);
            btn.onclick = minimizeTL;
        } else if (isSubChildOf(modebars[i], "app-window-bottom")) {
            groupDiv = document.createElement("div");
            groupDiv.classList.add('modebar-group');
            modebars[i].firstChild.appendChild(groupDiv);

            btn = newButton('maximizeBtn-B', 'Maximize', 'expand.svg');
            groupDiv.appendChild(btn);
            btn.onclick = maximizeB;

            btn = newButton('minimizeBtn-B', 'Minimize', 'collapse.svg');
            groupDiv.appendChild(btn);
            btn.onclick = minimizeB;
        }
    }

}

appInit();