// Path: src\ui\js\script.js
class VLANVision {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.data = null;
    }

    init() {
        console.log('VLANVision is initializing...');
        this.loadData();
        this.addEventListeners();
        this.handleFirewallFormSubmit();
    }

    async createVlan(vlanId, name, description) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/vlan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vlan_id: vlanId, name, description }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('VLAN created successfully');
        } catch (error) {
            console.error('Failed to create VLAN:', error);
        }
    }

    async updateVlan(vlanId, name, description) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/vlan/${vlanId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('VLAN updated successfully');
        } catch (error) {
            console.error('Failed to update VLAN:', error);
        }
    }

    async deleteVlan(vlanId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/vlan/${vlanId}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('VLAN deleted successfully');
        } catch (error) {
            console.error('Failed to delete VLAN:', error);
        }
    }

    async getVlans() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/vlan`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('VLANs fetched successfully', data.vlans);
            return data.vlans;
        } catch (error) {
            console.error('Failed to fetch VLANs:', error);
        }
    }

    handleUserInput(event) {
        const target = event.target;
        if (target.matches('.dashboard-link')) {
            this.loadData();
        } else if (target.matches('#integrate-grafana-button')) {
            this.integrateGrafana();
        } else if (target.matches('#integrate-node-red-button')) {
            this.integrateNodeRED();
        } else if (target.matches('.modal-button')) {
            this.displayFirewallFormModal(target);
        }
    }

    displayFirewallFormModal(target) {
        const modalId = target.dataset.modalTarget;
        const modal = document.querySelector(modalId);
        modal.classList.add('show');
    }

    handleFirewallFormSubmit() {
        const firewallForm = document.getElementById('firewall-form');
        if (!firewallForm) return;

        firewallForm.addEventListener('submit', async event => {
            event.preventDefault();

            const rule = document.getElementById('rule').value;
            if (!rule) return;

            try {
                const response = await fetch(`${this.apiBaseUrl}/api/firewall`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rule }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                console.log('Firewall rule added successfully');
            } catch (error) {
                console.error('Failed to add firewall rule:', error);
            }
        });
    }

    async loadData() {
    try {
        const response = await fetch(`${this.apiBaseUrl}/api/data`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}, URL: ${response.url}`);
        }
        this.data = await response.json();
        this.updateUI();
    } catch (error) {
        console.error('Error:', error);
        // Check if error is due to network failure
        if (error instanceof TypeError) {
            alert('Network error, please check your connection and try again');
        } else {
            alert(`Failed to load data due to: ${error.message}`);
        }
    }

    updateUI() {
        if (!this.data) return;
        // Update the UI based on this.data
        // ...
    }

    addEventListeners() {
        document.body.addEventListener('click', event => this.handleUserInput(event));
        this.handleDropdownMenu();
        this.handleModals();
        this.addFirewallFormEventListener();
    }

    handleUserInput(event) {
        const target = event.target;
        if (!target.matches('.dashboard-link')) return;
        this.loadData();
        // Add other event handling logic...
    }

    addFirewallFormEventListener() {
        const firewallForm = document.getElementById('firewall-form');
        const addFirewallRuleButton = document.getElementById('add-firewall-rule-button');

        if (!addFirewallRuleButton) return;

        addFirewallRuleButton.addEventListener('click', function() {
            firewallForm.classList.remove('hidden');
        });
    }

    async integrateTool(toolName) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/${toolName.toLowerCase()}`, { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log(`${toolName} integrated successfully`);
        } catch (error) {
            console.error(`Failed to integrate ${toolName}:`, error);
        }
    }

    async integrateGrafana() {
        return this.integrateTool('Grafana');
    }

    async integrateNodeRED() {
        return this.integrateTool('Node-RED');
    }

    // Method to handle dropdowns in the navbar
    handleDropdownMenu() {
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('mouseenter', function() {
                this.children[1].classList.add('show');
            });
            dropdown.addEventListener('mouseleave', function() {
                this.children[1].classList.remove('show');
            });
        });
    }

    // Method to handle modals
    handleModals() {
        const modals = document.querySelectorAll('.modal');
        const modalButtons = document.querySelectorAll('.modal-button');
        const closeButtons = document.querySelectorAll('.close-modal');

        modalButtons.forEach(button => {
            button.addEventListener('click', function() {
                const modal = document.querySelector(this.dataset.modalTarget);
                modal.classList.add('show');
            });
        });

        closeButtons.forEach(button => {
            button.addEventListener('click', function() {
                const modal = this.closest('.modal');
                modal.classList.remove('show');
            });
        });

        modals.forEach(modal => {
            modal.addEventListener('click', function() {
                this.classList.remove('show');
            });
        });
    }

    // Method to update breadcrumb
    updateBreadcrumb(section) {
        const breadcrumb = document.querySelector('.breadcrumb');
        breadcrumb.innerHTML = `<li class="breadcrumb-item"><a href="#${section}">${section}</a></li>`;
    }
}

const vlanVisionApp = new VLANVision('http://localhost:5000');
document.addEventListener('DOMContentLoaded', () => vlanVisionApp.init());