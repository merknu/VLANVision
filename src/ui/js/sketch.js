// Path: src\ui\js\sketch.js
let vlanBoxes = [];
let history = [];
let future = [];

let currentBox = null;

// Create VLANVision instance and make it globally accessible
const vlanVisionApp = new VLANVision('http://localhost:5000');

function setup() {
    let canvas = createCanvas(800, 600);
    canvas.parent('vlanCanvas');

    // Fetch initial VLAN boxes from server
    vlanVisionApp.getVlans().then((vlans) => {
        for (let vlan of vlans) {
            vlanBoxes.push(new VlanBox(random(width), random(height), 80, 30, vlan.id));
        }

        // Push the initial state onto the history stack
        history.push(JSON.parse(JSON.stringify(vlanBoxes)));
    });
}

function draw() {
    background(240);
    for (let box of vlanBoxes) {
        box.show();
    }
}

function mousePressed() {
    let hitBox = false;

    for (let box of vlanBoxes) {
        if (box.hit(mouseX, mouseY)) {
            currentBox = box;
            hitBox = true;
        }
    }

    // If the mouse press was not on a box, add a new one
    if (!hitBox) {
        let id = vlanBoxes.length > 0 ? Math.max(...vlanBoxes.map(box => box.id)) + 1 : 1;
        vlanBoxes.push(new VlanBox(mouseX, mouseY, 80, 30, id));
        updateHistory();

        // Create VLAN on server
        vlanVisionApp.createVlan(id, `VLAN ${id}`, 'Generated by VLAN Vision').then(() => {
            console.log(`VLAN ${id} created on server`);
        });
    }
}

function mouseReleased() {
    if (currentBox != null) {
        currentBox = null;
        updateHistory();
    }
}

function keyPressed() {
    if (key === 'z' || key === 'Z') {
        undo();
    } else if (key === 'y' || key === 'Y') {
        redo();
    } else if (key === 'x' || key === 'X') {
        removeVlan();
    }
}

function updateHistory() {
    history.push(JSON.parse(JSON.stringify(vlanBoxes)));
    future = [];
}

function undo() {
    if (history.length > 1) {
        future.unshift(history.pop());
        vlanBoxes = JSON.parse(JSON.stringify(history[history.length - 1]));
    }
}

function redo() {
    if (future.length > 0) {
        history.push(future.shift());
        vlanBoxes = JSON.parse(JSON.stringify(history[history.length - 1]));
    }
}

function removeVlan() {
    if (currentBox != null) {
        let id = currentBox.id;
        vlanBoxes = vlanBoxes.filter(box => box.id !== id);
        updateHistory();

        // Delete VLAN from server
        vlanVisionApp.deleteVlan(id).then(() => {
            console.log(`VLAN ${id} deleted from server`);
        });
    }
}

// VlanBox class
class VlanBox {
    constructor(x, y, w, h, id) {
        this.x = x;
        this.y = y;
        this.w = w;
        this.h = h;
        this.id = id;
    }

    hit(x, y) {
        if (x > this.x && x < this.x + this.w && y > this.y && y < this.y + this.h) {
            return true;
        }
        return false;
    }

    show() {
        stroke(0);
        if (currentBox === this) {
            fill(127);
        } else {
            fill(255);
        }
        rect(this.x, this.y, this.w, this.h);
        fill(0);
        text(`VLAN ${this.id}`, this.x + 5, this.y + this.h / 2);
    }
}
