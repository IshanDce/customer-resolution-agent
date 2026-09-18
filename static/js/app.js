/**
 * AeroResolve AI - Core Application Controller
 */

import { api } from './api.js';
import { components } from './components.js';

class AppController {
  constructor() {
    this.currentPnr = 'SK4821X'; // Default to Priya Nair
    this.currentCustomer = null;
    this.currentSentiment = 'neutral';
    this.currentGuardrails = null;
    this.apiProvider = 'gemini';
    this.apiKey = '';
    this.selectedTicketId = null;

    this.init();
  }

  async init() {
    this.bindEvents();
    await this.loadCustomers();
    await this.selectScenario(this.currentPnr);
    await this.loadCustomerTicketCard();
  }

  bindEvents() {
    // Send message form
    const sendBtn = document.getElementById('btn-send');
    const chatInput = document.getElementById('chat-input');

    sendBtn.addEventListener('click', () => this.handleSendMessage());
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSendMessage();
      }
    });

    // Reset System Button
    document.getElementById('btn-reset').addEventListener('click', () => this.handleReset());

    // Custom Passenger Modal
    const customModal = document.getElementById('modal-custom-passenger');
    document.getElementById('btn-open-custom-modal').addEventListener('click', () => {
      customModal.classList.add('active');
    });
    document.getElementById('btn-close-custom-modal').addEventListener('click', () => {
      customModal.classList.remove('active');
    });
    document.getElementById('form-custom-passenger').addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleCreateCustomPassenger();
    });

    // Quick chips delegation
    document.getElementById('quick-chips').addEventListener('click', (e) => {
      if (e.target.classList.contains('chip-btn')) {
        const text = e.target.getAttribute('data-text');
        chatInput.value = text;
        this.handleSendMessage();
      }
    });

    // Admin Panel view
    document.getElementById('btn-open-admin').addEventListener('click', () => this.openAdminPanel());
    document.getElementById('btn-close-admin').addEventListener('click', () => this.closeAdminPanel());
    document.getElementById('admin-ticket-list').addEventListener('click', (e) => {
      const item = e.target.closest('.ticket-item');
      if (item) this.selectAdminTicket(item.getAttribute('data-ticket-id'));
    });
    document.getElementById('form-admin-reply').addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitAdminReply();
    });

    // Customer Ticket Thread modal
    document.getElementById('btn-open-ticket').addEventListener('click', () => this.openCustomerTicket());
    document.getElementById('btn-close-ticket').addEventListener('click', () => this.closeCustomerTicket());

  }

  async loadCustomers() {
    try {
      const customers = await api.getCustomers();
      const selectorContainer = document.getElementById('scenario-selector');
      selectorContainer.innerHTML = '';

      customers.forEach(cust => {
        const btn = document.createElement('button');
        btn.className = `scenario-btn ${cust.pnr === this.currentPnr ? 'active' : ''}`;
        btn.id = `scenario-btn-${cust.pnr}`;
        btn.onclick = () => this.selectScenario(cust.pnr);

        const tierClass = `tier-${cust.loyalty_tier.toLowerCase()}`;
        const booking = cust.bookings[0] || {};

        btn.innerHTML = `
          <div class="scenario-meta">
            <span class="scenario-name">${cust.name}</span>
            <span class="scenario-sub">${booking.flight_number} • ${booking.route}</span>
          </div>
          <span class="tier-badge ${tierClass}">${cust.loyalty_tier}</span>
        `;
        selectorContainer.appendChild(btn);
      });
    } catch (err) {
      console.error('Failed to load customers', err);
    }
  }

  async selectScenario(pnr) {
    this.currentPnr = pnr;

    // Update scenario buttons UI
    document.querySelectorAll('.scenario-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`scenario-btn-${pnr}`);
    if (activeBtn) activeBtn.classList.add('active');

    try {
      this.currentCustomer = await api.getCustomer(pnr);
      this.renderSidebar();
      await this.loadChatHistory();
      this.updateQuickChips();
      await this.loadCustomerTicketCard();
    } catch (err) {
      console.error('Failed to load customer dossier', err);
    }
  }

  renderSidebar() {
    const passportContainer = document.getElementById('customer-passport');
    passportContainer.innerHTML = components.renderPassport(this.currentCustomer);
  }

  async loadCustomerTicketCard() {
    const container = document.getElementById('customer-ticket-card');
    try {
      const tickets = await api.getTickets('customer', this.currentPnr);
      if (!tickets || tickets.length === 0) {
        container.innerHTML = components.renderCustomerTicketCard(null);
        return;
      }
      const ticket = await api.getTicket(tickets[0].ticket_id, 'customer', this.currentPnr);
      container.innerHTML = components.renderCustomerTicketCard(ticket);
    } catch (err) {
      console.error('Failed to load customer ticket card', err);
      container.innerHTML = components.renderCustomerTicketCard(null);
    }
  }

  async loadChatHistory() {
    const chatFeed = document.getElementById('chat-feed');
    chatFeed.innerHTML = '';

    const history = await api.getHistory(this.currentPnr);

    if (history.length === 0) {
      // Show clean empty state — no auto-triggered dummy messages
      this.renderEmptyState();
    } else {
      history.forEach(msg => {
        this.appendMessageToFeed(msg.role, msg.content, msg.action_cards);
      });
    }
  }

  renderEmptyState() {
    const feed = document.getElementById('chat-feed');
    const customer = this.currentCustomer;
    const booking = customer?.bookings?.[0] || {};
    const disruption = booking.disruption_type || 'none';
    const disruptionLabel = disruption === 'cancellation'
      ? `Flight ${booking.flight_number} has been cancelled`
      : disruption === 'delay'
        ? `Flight ${booking.flight_number} is delayed ${booking.delay_duration_hours}h`
        : `Flight ${booking.flight_number} — no active disruption`;

    feed.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">✈️</div>
        <div class="empty-title">Ready to assist ${customer?.name?.split(' ')[0] || 'you'}</div>
        <div class="empty-sub">${disruptionLabel}</div>
        <div class="empty-hint">Type your message below to start the conversation</div>
      </div>
    `;
  }

  updateQuickChips() {
    const chipsContainer = document.getElementById('quick-chips');
    let chips = [];

    if (this.currentPnr === 'SK4821X') {
      chips = [
        { label: "😡 Demand full refund + free business upgrade", text: "I'm furious that flight SK-204 got cancelled! I want a full cash refund plus a free upgrade to business class on my return flight for the trouble." },
        { label: "💳 Just process my full cash refund", text: "Please go ahead and process my full cash refund to my card." },
        { label: "✈️ Rebook me on next flight", text: "Can you rebook me on the next available flight to Goa?" },
        { label: "⚖️ Threaten legal action", text: "This is completely unacceptable, I am going to file a formal complaint and take legal action!" }
      ];
    } else if (this.currentPnr === 'TR1190B') {
      chips = [
        { label: "🏨 Demand hotel for 4h delay", text: "My flight is delayed 4 hours and I'm missing an important meeting! I want hotel accommodation since it's been such a long delay." },
        { label: "🥪 How do I use the meal voucher & lounge?", text: "Thank you, where is the lounge and how can I redeem this meal voucher?" },
        { label: "⚖️ Threaten formal complaint", text: "I'm going to file a formal complaint with the DGCA over this ruined business meeting!" }
      ];
    } else if (this.currentPnr === 'WL7742') {
      chips = [
        { label: "🏨 Demand full night hotel & ₹2,000 waiver", text: "I want a full night's hotel stay for this 6 hour delay, and I also want to be moved onto a higher-fare flight instead of waiting — please waive the ₹2,000 fare difference." },
        { label: "🛌 Where is the day-use transit hotel?", text: "Understood on the policy. Where do I check in for the transit day-room?" },
        { label: "💳 I will pay the ₹2,000 fare difference", text: "I can't wait until 20:00, please rebook me on the earlier flight and I will pay the ₹2,000 difference." }
      ];
    } else {
      chips = [
        { label: "ℹ️ Inquire about disruption options", text: "What are my compensation options for this flight disruption?" },
        { label: "💳 Request full refund", text: "I would like to cancel and request a full refund." },
        { label: "🏨 Ask about hotel accommodation", text: "Do I qualify for hotel accommodation during this delay?" }
      ];
    }

    chipsContainer.innerHTML = chips.map(c => `
      <button class="chip-btn" data-text="${c.text.replace(/"/g, '&quot;')}">${c.label}</button>
    `).join('');
  }

  async handleSendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    this.appendMessageToFeed('user', text);

    try {
      const res = await api.sendMessage(this.currentPnr, text, this.apiProvider, this.apiKey);
      this.appendMessageToFeed('assistant', res.reply, res.action_cards);

      this.currentSentiment = res.sentiment_detected;
      this.currentGuardrails = res.guardrails;
      await this.loadCustomerTicketCard();
    } catch (err) {
      console.error('Chat error', err);
      this.appendMessageToFeed('assistant', 'I apologize, an error occurred while connecting to the resolution service.');
    }
  }

  appendMessageToFeed(role, content, actionCards = []) {
    const feed = document.getElementById('chat-feed');
    const msgWrapper = document.createElement('div');
    msgWrapper.className = `message-wrapper ${role}`;

    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    let cardsHtml = '';
    if (actionCards && actionCards.length > 0) {
      cardsHtml = actionCards.map(c => components.renderActionCard(c)).join('');
    }

    // Convert basic newlines to breaks
    const formattedContent = content.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

    msgWrapper.innerHTML = `
      <div class="message-bubble">
        ${formattedContent}
        ${cardsHtml}
      </div>
      <div class="message-meta">
        <span>${role === 'user' ? 'Passenger' : role === 'admin' ? 'Support Admin' : 'AeroResolve Agent'}</span>
        <span>•</span>
        <span>${timeStr}</span>
      </div>
    `;

    feed.appendChild(msgWrapper);
    requestAnimationFrame(() => {
      feed.scrollTop = feed.scrollHeight;
    });
    setTimeout(() => {
      feed.scrollTop = feed.scrollHeight;
    }, 80);
  }

  // ── Admin Panel ──────────────────────────────────────────────────────────

  async openAdminPanel() {
    document.getElementById('admin-panel').classList.add('active');
    await this.loadAdminTickets();
  }

  async closeAdminPanel() {
    document.getElementById('admin-panel').classList.remove('active');
    // Refresh the customer-facing thread so any admin reply is visible immediately.
    await this.loadChatHistory();
    await this.loadCustomerTicketCard();
  }

  async loadAdminTickets() {
    try {
      const tickets = await api.getTickets('admin');
      const listContainer = document.getElementById('admin-ticket-list');
      listContainer.innerHTML = components.renderAdminTicketList(tickets, this.selectedTicketId);

      const detailContainer = document.getElementById('admin-ticket-detail');
      if (this.selectedTicketId) {
        const stillExists = tickets.some(t => t.ticket_id === this.selectedTicketId);
        if (stillExists) {
          await this.loadAdminTicketDetail(this.selectedTicketId);
          return;
        }
        this.selectedTicketId = null;
      }
      detailContainer.innerHTML = components.renderTicketDetail(null);
      document.getElementById('admin-reply-ticket-id').value = '';
    } catch (err) {
      console.error('Failed to load admin tickets', err);
    }
  }

  async selectAdminTicket(ticketId) {
    this.selectedTicketId = ticketId;
    document.querySelectorAll('.ticket-item').forEach(btn => btn.classList.remove('active'));
    const item = document.querySelector(`.ticket-item[data-ticket-id="${ticketId}"]`);
    if (item) item.classList.add('active');
    await this.loadAdminTicketDetail(ticketId);
  }

  async loadAdminTicketDetail(ticketId) {
    try {
      const ticket = await api.getTicket(ticketId, 'admin');
      document.getElementById('admin-ticket-detail').innerHTML = components.renderTicketDetail(ticket);
      document.getElementById('admin-reply-ticket-id').value = ticket.ticket_id;
    } catch (err) {
      console.error('Failed to load ticket detail', err);
    }
  }

  async submitAdminReply() {
    const ticketId = document.getElementById('admin-reply-ticket-id').value;
    const replyInput = document.getElementById('admin-reply-input');
    const reply = replyInput.value.trim();
    const resolve = document.getElementById('admin-reply-resolve').checked;
    if (!ticketId || !reply) return;

    try {
      await api.respondToTicket(ticketId, reply, resolve);
      replyInput.value = '';
      await this.loadAdminTicketDetail(ticketId);
      await this.loadAdminTickets();
      await this.loadCustomerTicketCard();
    } catch (err) {
      console.error('Admin reply failed', err);
      alert('Admin response failed. Please try again.');
    }
  }

  // ── Customer Ticket Thread ────────────────────────────────────────────────

  async openCustomerTicket() {
    document.getElementById('modal-customer-ticket').classList.add('active');
    await this.loadCustomerTicket();
  }

  closeCustomerTicket() {
    document.getElementById('modal-customer-ticket').classList.remove('active');
  }

  async loadCustomerTicket() {
    const pnr = this.currentPnr;
    const container = document.getElementById('customer-ticket-detail');

    try {
      const tickets = await api.getTickets('customer', pnr);
      if (!tickets || tickets.length === 0) {
        container.innerHTML = '<div class="ticket-empty">No support ticket has been created yet. Start a conversation to raise a ticket.</div>';
        return;
      }
      const ticket = await api.getTicket(tickets[0].ticket_id, 'customer', pnr);
      container.innerHTML = components.renderTicketDetail(ticket);
    } catch (err) {
      console.error('Failed to load customer ticket', err);
      container.innerHTML = '<div class="ticket-empty">Unable to load your ticket thread.</div>';
    }
  }

  async handleCreateCustomPassenger() {
    const pnr = document.getElementById('cust-pnr').value.trim().toUpperCase();
    const name = document.getElementById('cust-name').value.trim();
    const tier = document.getElementById('cust-tier').value;
    const email = document.getElementById('cust-email').value.trim();
    const phone = document.getElementById('cust-phone').value.trim();
    const flight = document.getElementById('cust-flight').value.trim();
    const route = document.getElementById('cust-route').value.trim();
    const status = document.getElementById('cust-status').value;
    const delayHours = parseFloat(document.getElementById('cust-delay-hours').value || 0);

    const payload = {
      pnr,
      name,
      loyalty_tier: tier,
      email,
      phone,
      flight_number: flight,
      route,
      date: "Wed 23 Sep 2026",
      scheduled_departure: "12:00",
      disruption_status: status,
      delay_hours: delayHours,
      airline_caused: true,
      flights_last_12m: 4,
      prior_complaint_issue: "Past query resolved smoothly"
    };

    await api.createCustomer(payload);
    document.getElementById('modal-custom-passenger').classList.remove('active');

    await this.loadCustomers();
    await this.selectScenario(pnr);
  }

  async handleReset() {
    if (confirm("Reset application to Assignment baseline data?")) {
      await api.resetSystem();
      await this.loadCustomers();
      await this.selectScenario('SK4821X');
      await this.loadCustomerTicketCard();
    }
  }
}

// Bootstrap app on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.app = new AppController();
});
