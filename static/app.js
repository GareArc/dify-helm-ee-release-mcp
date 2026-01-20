// Configuration
const API_BASE = '/api';

// Check authentication on page load
if (!isAuthenticated()) {
    redirectToLogin();
}

// API functions
async function fetchToolCalls() {
    try {
        const response = await authenticatedFetch(`${API_BASE}/tool-calls`);

        if (!response.ok) {
            throw new Error(`Failed to fetch tool calls: ${response.statusText}`);
        }

        const data = await response.json();
        return data.items || [];
    } catch (error) {
        // 401 errors are handled by authenticatedFetch (redirects to login)
        if (error.message === 'Authentication failed' || error.message === 'Not authenticated') {
            return [];
        }
        showError(error.message);
        return [];
    }
}

async function approveToolCall(toolCallId) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/tool-calls/${toolCallId}/approve`, {
            method: 'POST',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve tool call');
        }

        showSuccess('Tool call approved successfully');
        return true;
    } catch (error) {
        // 401 errors are handled by authenticatedFetch (redirects to login)
        if (error.message === 'Authentication failed' || error.message === 'Not authenticated') {
            return false;
        }
        showError(error.message);
        return false;
    }
}

async function rejectToolCall(toolCallId) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/tool-calls/${toolCallId}/reject`, {
            method: 'POST',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to reject tool call');
        }

        showSuccess('Tool call rejected successfully');
        return true;
    } catch (error) {
        // 401 errors are handled by authenticatedFetch (redirects to login)
        if (error.message === 'Authentication failed' || error.message === 'Not authenticated') {
            return false;
        }
        showError(error.message);
        return false;
    }
}

async function deleteToolCall(toolCallId) {
    if (!confirm('Are you sure you want to delete this tool call?')) {
        return false;
    }

    try {
        const response = await authenticatedFetch(`${API_BASE}/tool-calls/${toolCallId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete tool call');
        }

        showSuccess('Tool call deleted successfully');
        return true;
    } catch (error) {
        // 401 errors are handled by authenticatedFetch (redirects to login)
        if (error.message === 'Authentication failed' || error.message === 'Not authenticated') {
            return false;
        }
        showError(error.message);
        return false;
    }
}

// UI functions
function showError(message) {
    $('#error-message')
        .text(message)
        .fadeIn()
        .delay(5000)
        .fadeOut();
}

function showSuccess(message) {
    $('#success-message')
        .text(message)
        .fadeIn()
        .delay(3000)
        .fadeOut();
}

function formatJSON(obj) {
    try {
        return JSON.stringify(obj, null, 2);
    } catch (error) {
        return String(obj);
    }
}

function getStatusClass(status) {
    return `status-${status.toLowerCase()}`;
}

function escapeHtml(text) {
    return $('<div>').text(text).html();
}

function createToolCallCard(toolCall) {
    const isPending = toolCall.status === 'pending';
    
    const cardHtml = `
        <div class="tool-call-card" id="tool-call-${toolCall.tool_call_id}">
            <div class="tool-call-header">
                <div>
                    <div class="tool-call-id">ID: ${toolCall.tool_call_id}</div>
                    <div class="tool-name">${escapeHtml(toolCall.tool_name)}</div>
                </div>
                <span class="status-badge ${getStatusClass(toolCall.status)}">${toolCall.status}</span>
            </div>
            <div class="tool-args">${escapeHtml(formatJSON(toolCall.args))}</div>
            <div class="tool-call-actions">
                ${isPending ? `
                    <button class="btn btn-success" data-action="approve" data-id="${toolCall.tool_call_id}">
                        Approve
                    </button>
                    <button class="btn btn-danger" data-action="reject" data-id="${toolCall.tool_call_id}">
                        Reject
                    </button>
                ` : ''}
                <button class="btn btn-secondary" data-action="delete" data-id="${toolCall.tool_call_id}">
                    Delete
                </button>
            </div>
        </div>
    `;
    
    return $(cardHtml);
}

function renderToolCalls(toolCalls, statusFilter = 'all') {
    const $container = $('#tool-calls-container');
    const $emptyState = $('#empty-state');
    const $loading = $('#loading');

    $loading.hide();
    $container.empty();

    let filteredCalls = toolCalls;
    if (statusFilter !== 'all') {
        filteredCalls = toolCalls.filter(tc => tc.status === statusFilter);
    }

    if (filteredCalls.length === 0) {
        $emptyState.show();
    } else {
        $emptyState.hide();
        filteredCalls.forEach(toolCall => {
            $container.append(createToolCallCard(toolCall));
        });
    }
}

async function loadToolCalls(showLoading = true) {
    const $loading = $('#loading');
    const $container = $('#tool-calls-container');
    const $emptyState = $('#empty-state');

    if (showLoading) {
        $loading.show();
        $container.empty();
    }
    $emptyState.hide();

    const statusFilter = $('#status-filter').val();
    const toolCalls = await fetchToolCalls();
    renderToolCalls(toolCalls, statusFilter);
}

async function handleApprove(toolCallId) {
    const success = await approveToolCall(toolCallId);
    if (success) {
        await loadToolCalls();
    }
}

async function handleReject(toolCallId) {
    const success = await rejectToolCall(toolCallId);
    if (success) {
        await loadToolCalls();
    }
}

async function handleDelete(toolCallId) {
    const success = await deleteToolCall(toolCallId);
    if (success) {
        await loadToolCalls();
    }
}

// Event listeners
$(document).ready(function() {
    // Check authentication
    if (!isAuthenticated()) {
        redirectToLogin();
        return;
    }

    // Logout button
    $('#logout-btn').on('click', function() {
        if (confirm('Are you sure you want to logout?')) {
            removeAuthToken();
            redirectToLogin();
        }
    });

    // Refresh button
    $('#refresh-btn').on('click', function() {
        loadToolCalls();
    });

    // Status filter
    $('#status-filter').on('change', function() {
        const toolCalls = [];
        $('.tool-call-card').each(function() {
            const $card = $(this);
            const id = $card.attr('id').replace('tool-call-', '');
            const name = $card.find('.tool-name').text();
            const status = $card.find('.status-badge').text().trim();
            const argsText = $card.find('.tool-args').text();
            let args;
            try {
                args = JSON.parse(argsText);
            } catch {
                args = {};
            }
            toolCalls.push({ tool_call_id: id, tool_name: name, args, status });
        });
        const statusFilter = $('#status-filter').val();
        renderToolCalls(toolCalls, statusFilter);
    });

    // Handle tool call actions using event delegation
    $(document).on('click', '[data-action]', function() {
        const action = $(this).data('action');
        const toolCallId = $(this).data('id');
        
        if (action === 'approve') {
            handleApprove(toolCallId);
        } else if (action === 'reject') {
            handleReject(toolCallId);
        } else if (action === 'delete') {
            handleDelete(toolCallId);
        }
    });

    // Initial load
    loadToolCalls();

    // Auto-refresh every second (without showing loading indicator)
    setInterval(function() {
        loadToolCalls(false);
    }, 1000);
});
