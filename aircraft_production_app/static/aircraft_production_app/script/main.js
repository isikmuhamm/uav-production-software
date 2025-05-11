// Global değişkenler base.html'den geliyor ve doğru oldukları varsayılıyor:
// CSRF_TOKEN, API_LOGIN_URL, API_USER_ME_URL, API_APP_BASE_URL="/api", LOGIN_PAGE_URL, DASHBOARD_URL

let authToken = localStorage.getItem('authToken');
let currentUser = localStorage.getItem('currentUser') ? JSON.parse(localStorage.getItem('currentUser')) : null;
let workOrdersDataTable = null;

// Helper Functions
function showSpinner() { $('#loadingSpinner').show(); }
function hideSpinner() { $('#loadingSpinner').hide(); }

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function makeApiRequest(endpoint, method, data, successCallback, errorCallback, showLoading = true) {
    if (showLoading) showSpinner();

    // API_APP_BASE_URL sonunda / olmamalı, endpoint başında / olmamalı.
    // Örnek: API_APP_BASE_URL = "/api"; endpoint = "work-orders/";
    // Sonuç: "/api/work-orders/"
    let fullUrl;

    // Eğer endpointOrFullUrl zaten API_APP_BASE_URL ile başlıyorsa veya genel bir /api/ ile başlıyorsa,
    // onu doğrudan kullan. Değilse, API_APP_BASE_URL'i başına ekle.
    if (endpoint.startsWith(API_APP_BASE_URL) || endpoint.startsWith('/api/')) {
        fullUrl = endpoint;
    } else {
        // API_APP_BASE_URL sonunda / olmamalı, endpointOrFullUrl başında / olmamalı.
        // Örnek: API_APP_BASE_URL = "/api"; endpointOrFullUrl = "work-orders/";
        // Sonuç: "/api/work-orders/"
        fullUrl = `${API_APP_BASE_URL}/${endpoint}`;
    }

    fullUrl = fullUrl.replace(/\/\//g, '/');

    // console.log("Requesting URL:", fullUrl); // DEBUG için

    const requestSettings = {
        url: fullUrl,
        method: method,
        headers: {
            'Authorization': authToken ? `Token ${authToken}` : '',
            // 'X-CSRFToken': getCookie('csrftoken') // Token auth için genellikle gerekmez
        },
        success: function(response) {
            if (showLoading) hideSpinner();
            if (successCallback) successCallback(response);
        },
        error: function(xhr) {
            // ... (Bir önceki mesajdaki detaylı hata yönetimi burada olmalı) ...
            if (showLoading) hideSpinner();
            let errorMessage = `API isteği başarısız oldu (${xhr.status}).`;
            if (xhr.responseJSON) {
                if (xhr.responseJSON.detail) { errorMessage = xhr.responseJSON.detail; }
                else if (Array.isArray(xhr.responseJSON)) { errorMessage = xhr.responseJSON.join(' '); }
                else if (typeof xhr.responseJSON === 'object') { errorMessage = Object.entries(xhr.responseJSON).map(([key, value]) => `${key}: ${value.join ? value.join(', ') : value}`).join('; ');}
                else { errorMessage = JSON.stringify(xhr.responseJSON); }
            } else if (xhr.status === 403) { errorMessage = "Bu işlem için yetkiniz bulunmamaktadır."; }
            else if (xhr.status === 401) {
                errorMessage = "Lütfen giriş yapınız.";
                if (window.location.pathname !== LOGIN_PAGE_URL) {
                    window.location.href = LOGIN_PAGE_URL + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
                }
            } else if (xhr.status === 0) { errorMessage = "Sunucuya ulaşılamıyor. Lütfen internet bağlantınızı kontrol edin."; }
            else if (xhr.statusText && xhr.statusText !== "error") { errorMessage = `Hata ${xhr.status}: ${xhr.statusText}`; }
            
            console.error("API Error:", xhr.status, errorMessage, xhr.responseText);
            if (errorCallback) errorCallback(errorMessage, xhr);
            else if (errorMessage && xhr.status !== 401 && xhr.status !== 0) {
                if (window.location.pathname !== LOGIN_PAGE_URL) { alert(errorMessage); }
                else if ($('#loginError').length) { $('#loginError').text(errorMessage); }
                else { alert(errorMessage); }
            }
        }
    };
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        requestSettings.data = JSON.stringify(data);
        requestSettings.contentType = 'application/json; charset=utf-8';
    } else if (data && method === 'GET') { // GET istekleri için data query string olarak gider
        requestSettings.data = data;
    }
    $.ajax(requestSettings);
}

// Giriş ve Kullanıcı Yönetimi
function handleLoginSubmit(event) {
    event.preventDefault();
    const username = $('#username').val();
    const password = $('#password').val();
    $('#loginError').text('');
    showSpinner();

    $.ajax({
        url: API_LOGIN_URL,
        method: 'POST',
        data: { username: username, password: password },
        success: function(response) {
            authToken = response.token;
            localStorage.setItem('authToken', authToken);
            fetchCurrentUserInfoAndRedirect();
        },
        error: function(xhr) {
            hideSpinner();
            let errorMsg = 'Giriş başarısız. Lütfen bilgilerinizi kontrol edin.';
            if (xhr.responseJSON && xhr.responseJSON.non_field_errors) {
                errorMsg = xhr.responseJSON.non_field_errors.join(', ');
            } else if (xhr.status === 400) {
                 errorMsg = "Kullanıcı adı veya şifre hatalı.";
            }
            $('#loginError').text(errorMsg);
        }
    });
}

function fetchCurrentUserInfoAndRedirect() {
    if (!authToken) {
        hideSpinner();
        if (window.location.pathname !== LOGIN_PAGE_URL) {
            window.location.href = LOGIN_PAGE_URL + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
        }
        return;
    }
    makeApiRequest(API_USER_ME_URL, 'GET', null,
        function(response) {
            currentUser = response;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            const nextUrlParams = new URLSearchParams(window.location.search).get('next');
            window.location.href = nextUrlParams || DASHBOARD_URL; 
        },
        function(errorMessage) {
            authToken = null; currentUser = null;
            localStorage.removeItem('authToken'); localStorage.removeItem('currentUser');
            if ($('#loginError').length) { // Eğer login sayfasındaysak
                 $('#loginError').text('Oturum bilgileri alınamadı veya token geçersiz. Lütfen tekrar giriş yapın.');
            } else if (window.location.pathname !== LOGIN_PAGE_URL) { // Login sayfasında değilsek login'e yönlendir
                window.location.href = LOGIN_PAGE_URL;
            }
        }
    );
}

function handleLogout() {
    authToken = null; currentUser = null;
    localStorage.removeItem('authToken'); localStorage.removeItem('currentUser');
    window.location.href = LOGIN_PAGE_URL;
}

function updateUserInfoDisplayAndMenus() {
    if (!currentUser && authToken) {
        makeApiRequest(API_USER_ME_URL, 'GET', null,
            function(response) {
                currentUser = response; localStorage.setItem('currentUser', JSON.stringify(currentUser));
                applyUserRolesToUI();
            },
            function() { handleLogout(); }
        );
    } else if (currentUser) {
        applyUserRolesToUI();
    } else {
        if (window.location.pathname !== LOGIN_PAGE_URL && !window.location.pathname.includes("public")) {
            window.location.href = LOGIN_PAGE_URL + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
        }
    }
}

function applyUserRolesToUI() {
    if (!currentUser) return;
    $('#currentUserUsername').text(currentUser.username || 'Kullanıcı');
    let roleDisplay = "Personel";
    $('.user-role-menu').hide(); $('.user-role-content').hide();
    if (currentUser.is_superuser || currentUser.is_staff) {
        roleDisplay = "Admin"; $('.user-role-admin').show();
    } else if (currentUser.personnel_profile && currentUser.personnel_profile.team_type) {
        const teamTypeKey = currentUser.personnel_profile.team_type;
        roleDisplay = currentUser.personnel_profile.team_type_display || teamTypeKey;
        if (teamTypeKey === 'ASSEMBLY_TEAM') { $('.user-role-assembler').show(); }
        else if (['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(teamTypeKey)) { $('.user-role-producer').show(); }
    }
    $('#currentUserRole').text(roleDisplay);
    if (!window.location.hash && $('.page-content.active').length === 0) {
        const firstVisibleMenuTarget = $('.user-role-menu:visible').first().find('.page-link').data('target') || 'dashboardContent';
        loadContent(firstVisibleMenuTarget);
    }
}

function loadContent(contentId) {
    if (!contentId) contentId = 'dashboardContent';
    $('.page-content').removeClass('active').hide();
    $('#' + contentId).addClass('active').show();
    $('.sidebar .nav-link.page-link').removeClass('active');
    $(`.sidebar .nav-link.page-link[data-target="${contentId}"]`).addClass('active');

    if (contentId !== 'dashboardContent') { window.location.hash = contentId.replace('Content', ''); }
    else { history.pushState("", document.title, window.location.pathname + window.location.search); }

    // API_APP_BASE_URL global değişkenini kullanarak URL oluştur
    if (contentId === 'workOrdersContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchWorkOrders(); populateWorkOrderFormDropdowns(); }
    else if (contentId === 'stockLevelsContent') { fetchStockLevels(); }
    else if (contentId === 'aircraftsContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchAircrafts(); }
    else if (contentId === 'partsContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchParts(); }
    else if (contentId === 'assignedWorkOrdersContent' && currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM') { fetchAssignedWorkOrders(); }
    else if (contentId === 'assembleAircraftContent' && currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM') { populateAssembleAircraftFormDropdowns(); }
    else if (contentId === 'producePartContent' && currentUser?.personnel_profile && ['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(currentUser.personnel_profile.team_type)) { populateProducePartFormDropdowns(); }
    else if (contentId === 'myTeamPartsContent' && currentUser?.personnel_profile && ['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(currentUser.personnel_profile.team_type)) { fetchMyTeamParts(); }
}

// --- API Çağrı Fonksiyonları (API_APP_BASE_URL Kullanımı) ---
// Her API çağrısında URL'in doğru oluşturulduğundan emin olalım.
// API_APP_BASE_URL (örn: "/api") sonunda / OLMAMALI.
// Endpoint (örn: "work-orders/") başında / OLMAMALI.
// Birleştirme: `${API_APP_BASE_URL}/${endpoint}`

function fetchWorkOrders() {
    const workOrderTableElement = $('#workOrdersTable');
    $('#workOrderAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') {
        console.error("DataTables JS kütüphanesi yüklenmemiş!");
        $('#workOrderAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>');
        return;
    }

    if ($.fn.DataTable.isDataTable(workOrderTableElement)) {
        if (workOrdersDataTable) { workOrdersDataTable.ajax.reload(null, false); }
        else { workOrderTableElement.DataTable().ajax.reload(null, false); }
        return;
    }
    
    console.log("Initializing WorkOrders DataTable...");
    workOrdersDataTable = workOrderTableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}work-orders/`, // API_APP_BASE_URL + / + endpoint
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) { /* ... */ },
            error: function (xhr, error, thrown) { /* ... (bir önceki gibi) ... */
                hideSpinner();
                let errorMsg = "İş emirleri DataTable ile yüklenirken bir hata oluştu.";
                if (xhr.responseJSON && xhr.responseJSON.detail) { errorMsg = xhr.responseJSON.detail;}
                else if (xhr.status === 403) { errorMsg = "İş emirlerini görüntüleme yetkiniz yok.";}
                $('#workOrderAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
                console.error("DataTable Ajax Error:", xhr.status, errorMsg, xhr.responseText);
            }
        },
        columns: [
            // ... (bir önceki mesajdaki columns tanımınız doğruydu) ...
            { data: "id", title: "ID" },
            { data: "aircraft_model_name", title: "Uçak Modeli", defaultContent: "-" },
            { data: "quantity", title: "Miktar" },
            {  data: "status_display", title: "Durum", render: function(data, type, row) { /* badge render */ 
                let badgeClass = 'bg-light text-dark'; 
                if (row.status === 'PENDING') badgeClass = 'bg-warning text-dark';
                else if (row.status === 'ASSIGNED') badgeClass = 'bg-primary text-white';
                else if (row.status === 'IN_PROGRESS') badgeClass = 'bg-info text-dark';
                else if (row.status === 'COMPLETED') badgeClass = 'bg-success text-white';
                else if (row.status === 'CANCELLED') badgeClass = 'bg-danger text-white';
                return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
            }},
            { data: "assigned_to_assembly_team_name", title: "Atanan Takım", defaultContent: "-" },
            { data: "created_by_username", title: "Oluşturan", defaultContent: "-" },
            { data: "created_at", title: "Oluşturma Tarihi", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            { data: null, title: "İşlemler", orderable: false, searchable: false, render: function (data, type, row) { /* butonlar */
                let buttons = '';
                if (currentUser && (currentUser.is_staff || currentUser.is_superuser)) {
                    buttons += `<button class="btn btn-sm btn-warning btn-edit-wo me-1" data-id="${row.id}" data-bs-toggle="modal" data-bs-target="#newWorkOrderModal" title="Düzenle"><i class="fas fa-edit"></i></button>`;
                    if (row.status !== 'CANCELLED' && row.status !== 'COMPLETED') {
                         buttons += `<button class="btn btn-sm btn-danger btn-delete-wo" data-id="${row.id}" title="İptal Et"><i class="fas fa-trash-alt"></i></button>`;
                    }
                }
                return buttons || '-';
            }}
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL }, // Global değişkenden al
        responsive: true,
        pageLength: 10,
        lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}



function createAircraftModelSelector(containerId, models, inputRadioName, isRadio = false, selectedValue = null) {
    const container = $(`#${containerId}`);
    container.empty();

    if (!models || models.length === 0) {
        container.append('<p class="text-muted small mt-1">Uygun uçak modeli bulunamadı.</p>');
        return;
    }

    if (isRadio) {
        container.addClass('row g-2 aircraft-model-selector-grid'); // Grid için class'lar
        models.forEach(model => {
            const isChecked = model.id == selectedValue ? 'checked' : '';
            const uniqueRadioId = `${inputRadioName}_${model.id}`; // Her radyo butonu için benzersiz ID
            
            // console.log(`Rendering Model: ${model.name_display}, Image URL: ${model.image_url}, ID: ${model.id}`);

            container.append(`
                <div class="col-6 col-md-4 col-lg-3 mb-2">
                    <div class="card h-100 text-center aircraft-model-card ${isChecked ? 'selected' : ''}" data-model-id="${model.id}">
                        <label for="${uniqueRadioId}" class="card-body d-flex flex-column justify-content-between align-items-center p-2" style="cursor:pointer; min-height: 160px;">
                            <img src="${model.image_url || ''}" alt="${model.name_display}" class="img-fluid mb-2" style="max-height: 80px; object-fit: contain; display: block; margin-left: auto; margin-right: auto;">
                            <h6 class="card-title small mb-0 mt-auto">${model.name_display}</h6>
                            <input type="radio" name="${inputRadioName}" id="${uniqueRadioId}" value="${model.id}" class="form-check-input visually-hidden" ${isChecked}>
                        </label>
                    </div>
                </div>
            `);
        });
        // Tıklama ile seçimi yönet
        // Event delegation kullanalım, çünkü kartlar dinamik olarak ekleniyor.
        container.off('click', '.aircraft-model-card').on('click', '.aircraft-model-card', function() {
            // Aynı gruptaki diğer seçimleri kaldır
            $(`input[name="${inputRadioName}"]`).closest('.aircraft-model-card').removeClass('selected');
            $(this).addClass('selected');
            $(this).find('input[type="radio"]').prop('checked', true).trigger('change');
        });

    } else { // Standart dropdown
        container.removeClass('row g-2 aircraft-model-selector-grid');
        const select = $('<select class="form-select">').attr('id', containerId + '_select').attr('name', inputRadioName).prop('required', true);
        select.append('<option value="">Model Seçiniz...</option>');
        models.forEach(model => {
            const isSelected = model.id == selectedValue ? 'selected' : '';
            select.append(`<option value="${model.id}" ${isSelected}>${model.name_display}</option>`);
        });
        container.append(select);
    }
}


// populateWorkOrderFormDropdowns fonksiyonu, uçak modeli seçimi için
// createAircraftModelSelector fonksiyonunu çağırmalı.
// Bu fonksiyonun doğru container ID'sini kullandığından emin olun.
function populateWorkOrderFormDropdowns(editData = null) {
    // Uçak Modelleri (Görsel Seçici)
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.results || modelsResponse;
        createAircraftModelSelector('woAircraftModelContainer', models, 'wo_aircraft_model', true, editData ? editData.aircraft_model : null);
    });

    // Montaj Takımları (Dropdown)
    makeApiRequest(`teams/?team_type=ASSEMBLY_TEAM`, 'GET', null, function(teamsResponse) {
        const teams = (teamsResponse.results || teamsResponse);
        const select = $('#woAssignedTeam');
        select.empty().append('<option value="">Takım Seçiniz:</option>');
        teams.forEach(team => {
            const isSelected = editData && team.id == editData.assigned_to_assembly_team ? 'selected' : '';
            select.append(`<option value="${team.id}" ${isSelected}>${team.name} (${team.team_type_display})</option>`);
        });
        if (editData) $('#woAssignedTeam').val(editData.assigned_to_assembly_team);
    });

    if (editData) {
        $('#woQuantity').val(editData.quantity);
        $('#woTargetDate').val(editData.target_completion_date || '');
        $('#woNotes').val(editData.notes || '');
        $('#newWorkOrderModal').data('edit-id', editData.id); // Düzenleme ID'sini sakla
        $('#newWorkOrderModalLabel').text(`İş Emrini Düzenle #${editData.id}`);
    } else {
        $('#newWorkOrderForm')[0].reset();
        $('#newWorkOrderModal').removeData('edit-id');
        $('#newWorkOrderModalLabel').text('Yeni İş Emri Oluştur');
        // createAircraftModelSelector zaten container'ı temizleyip yeniden oluşturur.
    }
}

// saveWorkOrder ve deleteWorkOrder fonksiyonları DataTable'ı yeniden yüklemeli
function saveWorkOrder(workOrderId = null) {
    // ... (mevcut form data toplama ve validasyon kodunuz) ...
    const formData = { aircraft_model: $('input[name="wo_aircraft_model"]:checked').val(), quantity: parseInt($('#woQuantity').val()), assigned_to_assembly_team: $('#woAssignedTeam').val() || null, target_completion_date: $('#woTargetDate').val() || null, notes: $('#woNotes').val() };
    if (!formData.aircraft_model) { $('#newWorkOrderError').text("Lütfen bir uçak modeli seçin."); return; }
    if (!formData.quantity || formData.quantity < 1) { $('#newWorkOrderError').text("Lütfen geçerli bir miktar girin."); return; }
    $('#newWorkOrderError').text("");

    const method = workOrderId ? 'PUT' : 'POST';
    const endpoint = workOrderId ? `work-orders/${workOrderId}/` : `work-orders/`;
    makeApiRequest(endpoint, method, formData,
        function(response) {
            $('#newWorkOrderModal').modal('hide');
            $('#workOrderAlerts').html(`<div class="alert alert-success alert-dismissible fade show" role="alert">İş emri başarıyla ${workOrderId ? 'güncellendi' : 'oluşturuldu'}.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`);
            if (workOrdersDataTable) { // DataTable'ı yeniden yükle
                workOrdersDataTable.ajax.reload(null, false); // false: pagination'ı sıfırlama
            }
        },
        function(errorMsg) { $('#newWorkOrderError').text(errorMsg); }
    );
}

function deleteWorkOrder(workOrderId) {
    if (!confirm(`İş Emri #${workOrderId} iptal edilecek (geri alınamaz). Emin misiniz?`)) return;
    makeApiRequest(`work-orders/${workOrderId}/`, 'DELETE', null,
        function() {
            $('#workOrderAlerts').html(`<div class="alert alert-info alert-dismissible fade show" role="alert">İş Emri #${workOrderId} başarıyla iptal edildi.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`);
            if (workOrdersDataTable) { // DataTable'ı yeniden yükle
                workOrdersDataTable.ajax.reload(null, false);
            }
        },
        function(errorMsg) { $('#workOrderAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`); }
    );
}


function fetchStockLevels() {
    $('#stockDataContainer').html('<p>Stok verileri yükleniyor...</p>'); $('#stockWarnings').hide();
    makeApiRequest(`inventory/stock-levels/`, 'GET', null,
        function(response) {
            let html = ''; let hasWarning = false;
            if (response.part_stocks && response.part_stocks.length > 0) {
                html += '<h5 class="mt-3">Parça Stokları</h5>';
                html += '<div class="table-responsive"><table class="table table-sm table-striped table-hover"><thead><tr><th>Uçak Modeli</th><th>Parça Tipi</th><th>Mevcut</th><th>Diğer Durumlar</th><th>Uyarı</th></tr></thead><tbody>';
                response.part_stocks.forEach(ps => {
                    let other_statuses_html = Object.entries(ps.status_counts).filter(([key, count]) => key !== 'AVAILABLE' && count > 0).map(([key, count]) => `${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: ${count}`).join('<br>') || '-';
                    html += `<tr><td>${ps.aircraft_model_name}</td><td>${ps.part_type_category_display}</td><td><strong>${ps.total_available}</strong></td><td><small>${other_statuses_html}</small></td><td>${ps.warning_zero_stock ? '<span class="badge bg-danger">Stok Yok</span>' : '<span class="badge bg-success">Yeterli</span>'}</td></tr>`;
                    if(ps.warning_zero_stock) hasWarning = true;
                });
                html += '</tbody></table></div>';
            } else { html += '<p class="mt-3">Görüntülenecek parça stoğu bulunmuyor.</p>'; }

            if (response.aircraft_stocks && response.aircraft_stocks.length > 0) {
                html += '<h5 class="mt-4">Uçak Stokları</h5>';
                html += '<div class="table-responsive"><table class="table table-sm table-striped table-hover"><thead><tr><th>Uçak Modeli</th><th>Aktif</th><th>Diğer Durumlar</th></tr></thead><tbody>';
                response.aircraft_stocks.forEach(as => {
                    let other_statuses_ac_html = Object.entries(as.status_counts).filter(([key, count]) => key !== 'ACTIVE' && count > 0).map(([key, count]) => `${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: ${count}`).join('<br>') || '-';
                    html += `<tr><td>${as.aircraft_model_name}</td><td><strong>${as.total_active}</strong></td><td><small>${other_statuses_ac_html}</small></td></tr>`;
                });
                html += '</tbody></table></div>';
            } else { html += '<p class="mt-4">Görüntülenecek uçak stoğu bulunmuyor.</p>'; }
            $('#stockDataContainer').html(html);
            if(hasWarning) $('#stockWarnings').show();
        },
        function(errorMsg) { $('#stockDataContainer').html(`<p class="text-danger">Stok verileri yüklenirken hata oluştu: ${errorMsg}</p>`); }
    );
}

function populateAssembleAircraftFormDropdowns() {
    // Uçak Modelleri (Görsel Seçici)
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.results || modelsResponse;
        createAircraftModelSelector('assembleAircraftModelContainer', models, 'assemble_aircraft_model_radio', true);
    });

    // Uygun İş Emirleri (Dropdown)
    makeApiRequest(`work-orders/`, 'GET', { status: 'PENDING,ASSIGNED,IN_PROGRESS' }, function(ordersResponse) {
        const orders = ordersResponse.results || ordersResponse;
        const select = $('#assembleWorkOrder'); // Bu hala bir select dropdown
        select.empty().append('<option value="">İş Emri Seçiniz</option>');
        if (Array.isArray(orders)) {
            orders.forEach(order => {
                select.append(`<option value="${order.id}">#${order.id} - ${order.aircraft_model_name} (${order.quantity} adet) - Durum: ${order.status_display}</option>`);
            });
        }
    });
}


function handleAssembleAircraftFormSubmit(event) {
    event.preventDefault();
    const formData = {
        aircraft_model_id: parseInt($('input[name="assemble_aircraft_model_radio"]:checked').val()), // GÜNCELLENDİ
        work_order_id: $('#assembleWorkOrder').val() ? parseInt($('#assembleWorkOrder').val()) : null
    };
    if (!formData.aircraft_model_id) {
        $('#assembleAircraftAlerts').html('<div class="alert alert-danger">Lütfen bir uçak modeli seçin.</div>').show(); return;
    }
    // ... (geri kalan handleAssembleAircraftFormSubmit kodunuz)
    $('#assembleAircraftAlerts').empty().hide();
    makeApiRequest(`assembly/assemble-aircraft/`, 'POST', formData,
        function(response) {
            $('#assembleAircraftAlerts').html(`<div class="alert alert-success">Uçak başarıyla monte edildi! Seri No: ${response.serial_number}</div>`).show();
            $('#assembleAircraftForm')[0].reset();
            $('input[name="assemble_aircraft_model_radio"]').prop('checked', false).closest('.aircraft-model-card').removeClass('selected');
            if ($('#stockLevelsContent').is(':visible')) fetchStockLevels();
            if ($('#aircraftsContent').is(':visible')) fetchAircrafts();
        },
        function(errorMsg, xhr) { /* ... */ }
    );
}

function populateProducePartFormDropdowns() {
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.results || modelsResponse;
        // 'produce_part_model_radio' benzersiz input name
        createAircraftModelSelector('producePartAircraftModelContainer', models, 'produce_part_model_radio', true);
    });
}

function handleProducePartFormSubmit(event) {
    event.preventDefault();
    const formData = {
        aircraft_model_compatibility: parseInt($('input[name="produce_part_model_radio"]:checked').val()) // GÜNCELLENDİ
    };
    if (!formData.aircraft_model_compatibility) {
        $('#producePartAlerts').html('<div class="alert alert-danger">Lütfen uyumlu olacağı bir uçak modeli seçin.</div>').show(); return;
    }
    // ... (geri kalan handleProducePartFormSubmit kodunuz)
    $('#producePartAlerts').empty().hide();
    makeApiRequest(`parts/`, 'POST', formData,
        function(response) {
            $('#producePartAlerts').html(`<div class="alert alert-success">Parça başarıyla üretildi! Seri No: ${response.serial_number} (${response.part_type_display} - ${response.aircraft_model_compatibility_name} için)</div>`).show();
            $('#producePartForm')[0].reset();
            $('input[name="produce_part_model_radio"]').prop('checked', false).closest('.aircraft-model-card').removeClass('selected');
            if ($('#stockLevelsContent').is(':visible')) fetchStockLevels();
            if ($('#myTeamPartsContent').is(':visible')) fetchMyTeamParts();
        },
        function(errorMsg) { /* ... */ }
    );
}

function fetchAircrafts() { makeApiRequest(`aircraft/`, 'GET', null, function(response){ const aircrafts = response.results || response; $('#aircraftListContainer').html('<p>Admin - Uçak listesi buraya gelecek. (' + aircrafts.length + ' adet)</p>'); console.log("Admin Aircrafts:", aircrafts); }); }
function fetchParts() { makeApiRequest(`parts/`, 'GET', null, function(response){ const parts = response.results || response; $('#partListContainer').html('<p>Admin - Parça listesi buraya gelecek. (' + parts.length + ' adet)</p>'); console.log("Admin Parts:", parts); }); }
function fetchAssignedWorkOrders() { makeApiRequest(`work-orders/`, 'GET', null, function(response){ const workOrders = response.results || response; $('#assignedWorkOrderListContainer').html('<p>Montajcı - Atanmış İş Emirleri buraya gelecek. (' + workOrders.length + ' adet)</p>'); console.log("Assigned WorkOrders:", workOrders); }); }
function fetchMyTeamParts() { makeApiRequest(`parts/`, 'GET', null, function(response){ const parts = response.results || response; $('#myTeamPartsListContainer').html('<p>Üretimci - Takım Parçaları buraya gelecek. (' + parts.length + ' adet)</p>'); console.log("My Team Parts:", parts); }); }

// Sayfa Yüklendiğinde Çalışacaklar
$(document).ready(function() {
    if (typeof LOGIN_PAGE_URL === 'undefined' || typeof DASHBOARD_URL === 'undefined' || typeof API_LOGIN_URL === 'undefined' || typeof API_USER_ME_URL === 'undefined' || typeof API_APP_BASE_URL === 'undefined') {
        console.error("Global URL değişkenlerinden biri veya birkaçı tanımlanmamış!");
        alert("Uygulama başlatılırken kritik bir hata oluştu. Lütfen konsolu kontrol edin.");
        return;
    }

    const currentPath = window.location.pathname;
    const nextUrl = new URLSearchParams(window.location.search).get('next');

    if (currentPath.endsWith(LOGIN_PAGE_URL)) {
        $('#loginForm').on('submit', handleLoginSubmit);
        if (authToken && currentUser) { window.location.href = nextUrl || DASHBOARD_URL; }
    } else if (currentPath.startsWith(DASHBOARD_URL.substring(0, DASHBOARD_URL.lastIndexOf('/') + 1))) {
        if (!authToken) {
            window.location.href = LOGIN_PAGE_URL + "?next=" + encodeURIComponent(currentPath + window.location.search);
        } else {
            if (!currentUser) {
                makeApiRequest(API_USER_ME_URL, 'GET', null,
                    function(response) { currentUser = response; localStorage.setItem('currentUser', JSON.stringify(currentUser)); initializeDashboard(); },
                    function() { handleLogout(); }
                );
            } else { initializeDashboard(); }
        }
    } else {
        if (authToken && !currentUser) { fetchCurrentUserInfoAndRedirect(); }
        // else if (!authToken && currentPath !== "/" && currentPath !== "") { // Ana sayfa değilse login'e yönlendir
        //     window.location.href = LOGIN_PAGE_URL;
        // }
    }

    function initializeDashboard() {
        updateUserInfoDisplayAndMenus();
        let initialContent = 'dashboardContent';
        const hash = window.location.hash.substring(1);
        if(hash && $(`#${hash}Content`).length) { initialContent = `${hash}Content`; }
        loadContent(initialContent);

        $('#logoutButton').on('click', handleLogout);
        $('.sidebar .nav-link.page-link').on('click', function(e) { e.preventDefault(); const targetContentId = $(this).data('target'); loadContent(targetContentId); });
        $('#saveWorkOrderBtn').on('click', function() { const workOrderId = $('#newWorkOrderModal').data('edit-id'); saveWorkOrder(workOrderId); });
        $('#workOrderTableBody').on('click', '.btn-delete-wo', function() { const workOrderId = $(this).data('id'); deleteWorkOrder(workOrderId); });
        $('#workOrderTableBody').on('click', '.btn-edit-wo', function() {
            const workOrderId = $(this).data('id');
            $('#newWorkOrderModalLabel').text(`İş Emrini Düzenle #${workOrderId}`);
            $('#newWorkOrderModal').data('edit-id', workOrderId);
            populateWorkOrderFormDropdowns(); // Dropdownları doldur
            makeApiRequest(`work-orders/${workOrderId}/`, 'GET', null, 
                function(data) {
                    $('#woAircraftModel').val(data.aircraft_model);
                    $('#woQuantity').val(data.quantity);
                    $('#woAssignedTeam').val(data.assigned_to_assembly_team);
                    $('#woTargetDate').val(data.target_completion_date || '');
                    $('#woNotes').val(data.notes || '');
                    $('#newWorkOrderError').text('');
                },
                function(errorMsg) { $('#newWorkOrderError').text(`İş emri detayları yüklenemedi: ${errorMsg}`); $('#newWorkOrderModal').modal('hide'); }
            );
        });
        $('#newWorkOrderModal').on('hidden.bs.modal', function () { $('#newWorkOrderForm')[0].reset(); $('#newWorkOrderModalLabel').text('Yeni İş Emri Oluştur'); $(this).removeData('edit-id'); $('#newWorkOrderError').text(''); });
        $('#assembleAircraftForm').on('submit', handleAssembleAircraftFormSubmit);
        $('#producePartForm').on('submit', handleProducePartFormSubmit);
    }

    // İş emri düzenleme modalı açıldığında dropdown'ları doldur
    $('#workOrderTableBody').on('click', '.btn-edit-wo', function() {
        const workOrderId = $(this).data('id');
        $('#newWorkOrderModalLabel').text(`İş Emrini Düzenle #${workOrderId}`);
        $('#newWorkOrderModal').data('edit-id', workOrderId); // ID'yi modal'a kaydet
        
        makeApiRequest(`work-orders/${workOrderId}/`, 'GET', null, 
            function(data) {
                // Uçak modeli ve takım dropdown'larını populateWorkOrderFormDropdowns ile doldur,
                // sonra seçili değerleri ayarla.
                populateWorkOrderFormDropdowns(data); // editData olarak gönder
                // Diğer alanları da doldur (miktar, notlar vb.)
                // Bu, populateWorkOrderFormDropdowns içinde de yapılabilir.
            },
            function(errorMsg) { /* ... */ }
        );
    });
});
