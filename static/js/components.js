/**
 * AeroResolve AI - UI Component Renderers
 */

export const components = {
  renderPassport(customer) {
    if (!customer) return '<p class="text-dim">No passenger loaded</p>';

    const tierClass = `tier-${customer.loyalty_tier.toLowerCase()}`;
    const complaints = customer.travel_history.prior_complaints || [];

    let complaintsHtml = '';
    if (complaints.length > 0) {
      complaintsHtml = complaints.map(c => `
        <div class="prior-complaint-box">
          <div style="font-weight:600; color:#f59e0b;">Prior Case: ${c.issue}</div>
          <div style="color:#94a3b8; font-size:0.72rem;">Resolution: ${c.resolution} (${c.date})</div>
        </div>
      `).join('');
    } else {
      complaintsHtml = '<div class="prior-complaint-box" style="color:#10b981;">No prior complaints (Clean history)</div>';
    }

    return `
      <div class="card-header">
        <div class="card-title">
          <span>Passenger Dossier</span>
        </div>
        <span class="tier-badge ${tierClass}">${customer.loyalty_tier}</span>
      </div>
      <div class="passport-details">
        <div class="passport-row">
          <span class="passport-label">Name</span>
          <span class="passport-value">${customer.name}</span>
        </div>
        <div class="passport-row">
          <span class="passport-label">PNR / Ref</span>
          <span class="passport-value" style="color:var(--accent-cyan); font-family:monospace;">${customer.pnr}</span>
        </div>
        <div class="passport-row">
          <span class="passport-label">Contact</span>
          <span class="passport-value">${customer.phone}</span>
        </div>
        <div class="passport-row">
          <span class="passport-label">Past 12 Months</span>
          <span class="passport-value">${customer.travel_history.flights_last_12m} Completed Flights</span>
        </div>
        <div style="margin-top:4px;">
          <div class="passport-label" style="margin-bottom:6px;">CRM Case History</div>
          ${complaintsHtml}
        </div>
      </div>
    `;
  },

  renderFlightTracker(booking) {
    if (!booking) return '<p class="text-dim">No booking available</p>';

    let statusClass = 'status-on-time';
    let icon = '✈️';
    if (booking.disruption_type === 'cancellation') {
      statusClass = 'status-cancelled';
      icon = '❌';
    } else if (booking.disruption_type === 'delay') {
      statusClass = 'status-delayed';
      icon = '⏳';
    }

    const cities = booking.route.split('→').map(s => s.trim());
    const origin = cities[0] || 'Origin';
    const dest = cities[1] || 'Destination';

    return `
      <div class="card-header">
        <div class="card-title">
          <span>Flight Radar</span>
          <span style="font-size:0.75rem; color:var(--accent-sky); font-family:monospace;">#${booking.flight_number}</span>
        </div>
        <span class="status-badge ${statusClass}">${icon} ${booking.status}</span>
      </div>
      <div class="flight-tracker">
        <div class="flight-route-visual">
          <div class="route-point">
            <span class="route-city">${origin}</span>
            <span class="route-time">${booking.scheduled_departure}</span>
          </div>
          <div class="route-line">
            <span class="route-plane-icon">✈️</span>
          </div>
          <div class="route-point" style="text-align:right;">
            <span class="route-city">${dest}</span>
            <span class="route-time">${booking.revised_departure ? `New: ${booking.revised_departure}` : booking.date}</span>
          </div>
        </div>
        <div style="font-size:0.78rem; color:var(--text-dim); display:flex; justify-content:space-between; background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <span>Class: <strong>${booking.cabin_class || 'Economy'}</strong></span>
          <span>Airline-Caused: <strong>${booking.airline_caused ? 'Yes' : 'No'}</strong></span>
          <span>Fare: <strong>₹${booking.fare_paid.toLocaleString()}</strong></span>
        </div>
      </div>
    `;
  },

  renderActionCard(card) {
    const type = card.card_type;
    const data = card.data || {};

    if (type === 'meal_voucher') {
      return `
        <div class="action-card card-voucher">
          <div class="action-card-header" style="color:var(--warning-amber);">
            <span>🍔 Digital Meal Voucher Issued</span>
            <span style="font-size:1.1rem; font-weight:800;">${data.amount}</span>
          </div>
          <div class="action-card-body">
            <div><strong>Code:</strong> <code style="color:var(--accent-cyan);">${data.voucher_code}</code></div>
            <div><strong>Flight:</strong> ${data.flight_number}</div>
            <div><strong>Validity:</strong> ${data.expiry}</div>
            <div><strong>Locations:</strong> Terminal Dining</div>
          </div>
          <div style="font-size:0.72rem; color:var(--text-dim); display:flex; justify-content:space-between; align-items:center;">
            <span>Scan at food counter</span>
            <span>Issued: ${data.issued_at}</span>
          </div>
        </div>
      `;
    }

    if (type === 'lounge_pass') {
      return `
        <div class="action-card card-lounge">
          <div class="action-card-header" style="color:var(--accent-sky);">
            <span>🥂 Executive Lounge Access Pass</span>
            <span class="tier-badge tier-silver">VIP Access</span>
          </div>
          <div class="action-card-body">
            <div><strong>Pass Ref:</strong> <code style="color:#fff;">${data.pass_id}</code></div>
            <div><strong>Passenger:</strong> ${data.passenger_name}</div>
            <div><strong>Lounge:</strong> ${data.lounge_name}</div>
            <div><strong>Airport:</strong> ${data.airport}</div>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">
            ${(data.amenities || []).map(a => `<span style="font-size:0.68rem; background:rgba(14,165,233,0.15); color:var(--accent-sky); padding:2px 6px; border-radius:4px;">${a}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (type === 'hotel_voucher') {
      return `
        <div class="action-card card-hotel">
          <div class="action-card-header" style="color:var(--platinum-primary);">
            <span>🏨 Transit Hotel Day-Room Voucher</span>
            <span style="font-size:0.75rem; color:#fff;">Coverage: Delay Hours Only</span>
          </div>
          <div class="action-card-body">
            <div><strong>Booking ID:</strong> <code style="color:#fff;">${data.booking_ref}</code></div>
            <div><strong>Property:</strong> ${data.hotel_name}</div>
            <div><strong>Scope:</strong> ${data.coverage_type}</div>
            <div><strong>Check-Out:</strong> ${data.check_out}</div>
          </div>
          <div style="font-size:0.72rem; color:#d8b4fe; font-style:italic;">${data.note}</div>
        </div>
      `;
    }

    if (type === 'refund_receipt') {
      return `
        <div class="action-card card-refund">
          <div class="action-card-header" style="color:var(--success-emerald);">
            <span>💳 Full Refund Initiated</span>
            <span style="font-size:1.1rem; font-weight:800;">${data.amount}</span>
          </div>
          <div class="action-card-body">
            <div><strong>Receipt:</strong> <code>${data.refund_id}</code></div>
            <div><strong>Route:</strong> ${data.route}</div>
            <div><strong>Method:</strong> ${data.payment_destination}</div>
            <div><strong>Timeline:</strong> ${data.timeline}</div>
          </div>
          <div style="font-size:0.72rem; color:var(--success-emerald); font-weight:600;">Status: Full refund in accordance with Disruption Policy</div>
        </div>
      `;
    }

    if (type === 'rebooking_pass') {
      return `
        <div class="action-card card-rebooking">
          <div class="action-card-header" style="color:var(--accent-cyan);">
            <span>🎫 Priority Rebooked Boarding Pass</span>
            <span class="tier-badge tier-gold">Confirmed</span>
          </div>
          <div class="action-card-body">
            <div><strong>E-Ticket:</strong> <code>${data.eticket}</code></div>
            <div><strong>New Flight:</strong> ${data.confirmed_flight}</div>
            <div><strong>Departure:</strong> ${data.departure}</div>
            <div><strong>Seat:</strong> ${data.seat_assignment}</div>
          </div>
          <div style="font-size:0.72rem; color:var(--accent-cyan);">Fare Difference: ${data.fare_difference_paid}</div>
        </div>
      `;
    }

    if (type === 'escalation_ticket') {
      return `
        <div class="action-card card-escalation">
          <div class="action-card-header" style="color:var(--danger-rose);">
            <span>🚨 Supervisor Priority Escalation Ticket</span>
            <code>${data.ticket_id}</code>
          </div>
          <div class="action-card-body" style="grid-template-columns:1fr;">
            <div><strong>Reason:</strong> ${data.escalation_reason}</div>
            ${data.requested_waiver_amount ? `<div><strong>Requested Waiver:</strong> <span style="color:#f43f5e; font-weight:700;">${data.requested_waiver_amount} (Exceeds ₹1,500 Agent Limit)</span></div>` : ''}
            <div><strong>Status:</strong> ${data.status}</div>
          </div>
          <div style="font-size:0.72rem; color:#fca5a5;">Handed over to Duty Supervisor for executive waiver review.</div>
        </div>
      `;
    }

    return '';
  },

  renderHUD(guardrails, sentiment) {
    const sentimentColors = {
      furious: 'var(--danger-rose)',
      frustrated: 'var(--warning-amber)',
      anxious: 'var(--accent-sky)',
      neutral: 'var(--text-muted)',
      appreciative: 'var(--success-emerald)'
    };

    const sColor = sentimentColors[sentiment] || 'var(--text-muted)';

    let allowedItems = (guardrails?.allowed_actions || []).map(a => `
      <div class="policy-item allowed">
        <span style="color:var(--success-emerald); font-weight:700;">✔</span>
        <span>${a}</span>
      </div>
    `).join('');

    let prohibitedItems = (guardrails?.prohibited_actions_triggered || []).map(p => `
      <div class="policy-item prohibited">
        <span style="color:var(--danger-rose); font-weight:700;">🛡️</span>
        <span style="color:#fca5a5;"><strong>Blocked:</strong> ${p}</span>
      </div>
    `).join('');

    let policiesInvoked = (guardrails?.policies_invoked || []).map(pol => `
      <span style="font-size:0.7rem; background:var(--bg-surface-3); border:1px solid var(--border-subtle); padding:2px 8px; border-radius:4px; color:var(--accent-cyan);">${pol}</span>
    `).join('');

    return `
      <div class="card-header">
        <div class="card-title">
          <span>Agent Brain & Guardrails</span>
        </div>
        <span style="font-size:0.72rem; background:rgba(16,185,129,0.1); color:var(--success-emerald); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:99px;">Active</span>
      </div>

      <div class="hud-section">
        <div class="sentiment-indicator">
          <span style="font-size:0.8rem; color:var(--text-dim);">Detected Sentiment</span>
          <span style="font-size:0.82rem; font-weight:700; text-transform:uppercase; color:${sColor};">${sentiment || 'neutral'}</span>
        </div>

        <div>
          <div style="font-size:0.76rem; color:var(--text-dim); margin-bottom:6px;">Service Policies Invoked</div>
          <div style="display:flex; flex-wrap:wrap; gap:4px;">
            ${policiesInvoked || '<span class="text-dim" style="font-size:0.75rem;">Standard disruption rules</span>'}
          </div>
        </div>

        <div>
          <div style="font-size:0.76rem; color:var(--text-dim); margin-bottom:6px;">Guardrail Enforcement</div>
          <div class="policy-list">
            ${prohibitedItems}
            ${allowedItems || '<div style="font-size:0.75rem; color:var(--text-dim); padding:6px;">Awaiting customer interaction...</div>'}
          </div>
        </div>
      </div>
    `;
  },

  renderEscalations(escalations) {
    if (!escalations || escalations.length === 0) {
      return `
        <div class="card-header">
          <div class="card-title">Supervisor Queue (0)</div>
        </div>
        <div style="font-size:0.78rem; color:var(--text-dim); padding:12px; text-align:center;">
          No active escalation tickets. Cases are resolved within frontline agent authority.
        </div>
      `;
    }

    const items = escalations.map(esc => {
      const data = esc.data || esc;
      const ticketId = data.ticket_id || 'ESC';
      const isOpen = esc.status !== 'approved' && esc.status !== 'resolved';

      return `
        <div class="escalation-card ${isOpen ? 'open' : ''}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:var(--danger-rose);">${ticketId}</strong>
            <span style="font-size:0.68rem; color:${isOpen ? '#f43f5e' : '#10b981'}; font-weight:600;">
              ${isOpen ? 'URGENT REVIEW' : 'RESOLVED'}
            </span>
          </div>
          <div><strong>Customer:</strong> ${data.customer_name || data.pnr} (${data.loyalty_tier || ''})</div>
          <div style="color:var(--text-muted); font-size:0.74rem;">${data.escalation_reason || data.reason}</div>
          ${isOpen ? `
            <div class="escalation-actions">
              <button class="btn-resolve" onclick="window.resolveTicket('${ticketId}', 'approved', 'Approved by Duty Supervisor')">✔ Approve Waiver</button>
              <button class="btn-resolve" onclick="window.resolveTicket('${ticketId}', 'rejected', 'Declined per Policy')">✖ Decline</button>
            </div>
          ` : `
            <div style="color:#10b981; font-size:0.7rem;">Status: ${esc.supervisor_notes || 'Handled'}</div>
          `}
        </div>
      `;
    }).join('');

    return `
      <div class="card-header">
        <div class="card-title">Supervisor Queue (${escalations.length})</div>
      </div>
      <div class="escalation-list">
        ${items}
      </div>
    `;
  },

  renderTicketStatusBadge(status) {
    const safeStatus = (status || 'open').toLowerCase();
    const label = safeStatus.charAt(0).toUpperCase() + safeStatus.slice(1);
    return `<span class="ticket-status-badge status-${safeStatus}">${label}</span>`;
  },

  renderAdminTicketList(tickets, selectedTicketId = null) {
    if (!tickets || tickets.length === 0) {
      return '<div class="ticket-empty">No support tickets yet. Customer complaints will appear here.</div>';
    }

    const items = tickets.map(t => `
      <button class="ticket-item ${t.ticket_id === selectedTicketId ? 'active' : ''}" data-ticket-id="${t.ticket_id}">
        <div class="ticket-item-head">
          <span class="ticket-id">${t.ticket_id}</span>
          ${this.renderTicketStatusBadge(t.status)}
        </div>
        <div class="ticket-item-name">
          ${t.customer_name}
          <span class="ticket-tier">${t.loyalty_tier || 'Member'}</span>
        </div>
        <div class="ticket-item-subject">${t.subject || 'No subject'}</div>
        <div class="ticket-item-updated">${t.updated_at ? `Updated ${new Date(t.updated_at).toLocaleString()}` : ''}</div>
      </button>
    `).join('');

    return `
      <div class="ticket-list">
        ${items}
      </div>
    `;
  },

  renderThreadMessage(message) {
    const role = message.role || 'assistant';
    const label = role === 'user' ? 'Customer' : role === 'admin' ? 'Support Admin' : 'AeroResolve Agent';
    const cardsHtml = (message.action_cards || []).map(c => this.renderActionCard(c)).join('');
    const formattedContent = (message.content || '').replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

    return `
      <div class="thread-message ${role}">
        <div class="thread-message-meta"><span>${label}</span></div>
        <div class="thread-message-content">${formattedContent}</div>
        ${cardsHtml ? `<div class="thread-message-cards">${cardsHtml}</div>` : ''}
      </div>
    `;
  },

  renderTicketDetail(ticket) {
    if (!ticket) {
      return '<div class="ticket-empty">Select a ticket to view its full conversation and status history.</div>';
    }

    const threadHtml = (ticket.thread || [])
      .map(m => this.renderThreadMessage(m))
      .join('');

    const historyHtml = (ticket.status_history || [])
      .map(h => `
        <div class="ticket-history-entry">
          <span class="ticket-history-status">${h.status}</span>
          <span class="ticket-history-by">by ${h.by || 'system'}</span>
          <span class="ticket-history-at">${h.at ? new Date(h.at).toLocaleString() : ''}</span>
        </div>
      `).join('');

    return `
      <div class="ticket-detail">
        <div class="ticket-detail-head">
          <div class="ticket-detail-title">
            <span class="ticket-detail-id">${ticket.ticket_id}</span>
            ${this.renderTicketStatusBadge(ticket.status)}
          </div>
          <div class="ticket-detail-customer">
            ${ticket.customer_name} <span class="ticket-tier">${ticket.loyalty_tier || 'Member'}</span>
          </div>
          <div class="ticket-detail-subject">${ticket.subject || 'No subject'}</div>
        </div>

        <div class="ticket-detail-meta">
          <span>PNR: <strong>${ticket.pnr}</strong></span>
          <span>Flight: <strong>${ticket.flight_number || '—'}</strong></span>
          <span>Route: <strong>${ticket.route || '—'}</strong></span>
        </div>

        <div class="ticket-thread">
          ${threadHtml || '<div class="ticket-empty">No conversation messages yet.</div>'}
        </div>

        <div class="ticket-history">
          <div class="ticket-history-title">Status History</div>
          ${historyHtml || '<div class="ticket-empty">No status changes yet.</div>'}
        </div>
      </div>
    `;
  },

  renderCustomerTicketCard(ticket) {
    if (!ticket) {
      return `
        <div class="card-header">
          <div class="card-title"><span>Support Ticket</span></div>
        </div>
        <div class="customer-ticket-card-body">
          <div class="customer-ticket-queue">
            <div class="queue-icon">📨</div>
            <div class="queue-title">Your message is sent to the admin</div>
            <div class="queue-sub">Please wait for the admin to respond to your ticket.</div>
          </div>
        </div>
      `;
    }

    const statusMessage = {
      open: 'Your message has been sent to the admin. Please wait for the admin to respond to your ticket.',
      answered: 'An admin has responded to your ticket.',
      resolved: 'Your ticket has been resolved by the admin.'
    }[ticket.status] || 'Your message has been sent to the admin.';

    const queueIcon = ticket.status === 'open' ? '🕓' : ticket.status === 'answered' ? '📬' : '🎉';

    return `
      <div class="card-header">
        <div class="card-title"><span>Support Ticket</span></div>
        ${this.renderTicketStatusBadge(ticket.status)}
      </div>
      <div class="customer-ticket-card-body">
        <div class="ticket-structure">
          <div class="ticket-structure-row">
            <span>Ticket ID</span>
            <strong>${ticket.ticket_id}</strong>
          </div>
          <div class="ticket-structure-row">
            <span>Subject</span>
            <strong>${ticket.subject || '—'}</strong>
          </div>
          <div class="ticket-structure-row">
            <span>Status</span>
            <strong style="text-transform:capitalize;">${ticket.status}</strong>
          </div>
        </div>
        <div class="customer-ticket-queue">
          <div class="queue-icon">${queueIcon}</div>
          <div class="queue-title">${statusMessage}</div>
        </div>
      </div>
    `;
  }
};
