/**
 * AeroResolve AI - Backend API Client
 */

const API_BASE = '';

export const api = {
  async getInfo() {
    const res = await fetch(`${API_BASE}/api/info`);
    return await res.json();
  },

  async getPolicies() {
    const res = await fetch(`${API_BASE}/api/policies`);
    return await res.json();
  },

  async getCustomers() {
    const res = await fetch(`${API_BASE}/api/customers`);
    return await res.json();
  },

  async getCustomer(identifier) {
    const res = await fetch(`${API_BASE}/api/customers/${encodeURIComponent(identifier)}`);
    if (!res.ok) throw new Error('Customer not found');
    return await res.json();
  },

  async getHistory(pnr) {
    const res = await fetch(`${API_BASE}/api/history/${encodeURIComponent(pnr)}`);
    return await res.json();
  },

  async sendMessage(pnr, message, apiProvider = 'internal', apiKey = null) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pnr,
        message,
        api_provider: apiProvider,
        api_key: apiKey
      })
    });
    if (!res.ok) throw new Error('Chat failed');
    return await res.json();
  },

  async createCustomer(payload) {
    const res = await fetch(`${API_BASE}/api/customers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async getEscalations() {
    const res = await fetch(`${API_BASE}/api/escalations`);
    return await res.json();
  },

  async resolveEscalation(ticketId, status, notes) {
    const res = await fetch(`${API_BASE}/api/escalations/${ticketId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, notes })
    });
    return await res.json();
  },

  async getTickets(role = 'customer', pnr = null) {
    const params = new URLSearchParams({ role });
    if (pnr) params.set('pnr', pnr);
    const res = await fetch(`${API_BASE}/api/tickets?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load tickets');
    return await res.json();
  },

  async getTicket(ticketId, role = 'customer', pnr = null) {
    const params = new URLSearchParams({ role });
    if (pnr) params.set('pnr', pnr);
    const res = await fetch(`${API_BASE}/api/tickets/${encodeURIComponent(ticketId)}?${params.toString()}`);
    if (!res.ok) throw new Error('Ticket not found');
    return await res.json();
  },

  async respondToTicket(ticketId, reply, resolve = false) {
    const res = await fetch(`${API_BASE}/api/tickets/${encodeURIComponent(ticketId)}/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reply, resolve, role: 'admin' })
    });
    if (!res.ok) throw new Error('Admin response failed');
    return await res.json();
  },

  async resetSystem() {
    const res = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
    return await res.json();
  }
};
