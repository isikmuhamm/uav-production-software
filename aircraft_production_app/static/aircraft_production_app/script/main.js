// =================================================================================
// GLOBAL VARIABLES & CONFIGURATION
// =================================================================================

// Bu global değişkenler base.html içinde tanımlanır ve uygulamanın çeşitli yerlerinde kullanılır.
// CSRF_TOKEN: Django CSRF token'ı (AJAX POST istekleri için gerekli olabilir, ancak TokenAuthentication ile genellikle gerekmez).
// API_LOGIN_URL: Kullanıcı girişi için API endpoint URL'si.
// API_USER_ME_URL: Mevcut kullanıcı bilgilerini almak için API endpoint URL'si.
// API_APP_BASE_URL: Uygulamanın ana API endpoint'lerinin temel URL'si (örn: "/api/v1/app/").
// LOGIN_PAGE_URL: Kullanıcı giriş sayfasının URL'si.
// DASHBOARD_URL: Başarılı giriş sonrası yönlendirilecek ana panel URL'si.
// DATATABLES_TR_JSON_URL: DataTables eklentisi için Türkçe dil dosyasının URL'si.

/** @type {string|null} Kullanıcının kimlik doğrulama token'ı. localStorage'dan alınır. */
let authToken = localStorage.getItem('authToken');
/** @type {object|null} Mevcut giriş yapmış kullanıcı bilgileri. localStorage'dan alınır. */
let currentUser = localStorage.getItem('currentUser') ? JSON.parse(localStorage.getItem('currentUser')) : null;

// DataTable instance'ları
/** @type {jQuery|null} Admin parça listesi için DataTable instance'ı. */
let adminPartsDataTable = null;
/** @type {jQuery|null} Üretimci takımının parça listesi için DataTable instance'ı. */
let myTeamPartsDataTable = null;
/** @type {jQuery|null} Hava aracı listesi için DataTable instance'ı. */
let aircraftsDataTable = null;
/** @type {jQuery|null} İş emri listesi için DataTable instance'ı (Admin). */
let workOrdersDataTable = null;
/** @type {jQuery|null} Montajcıya atanmış iş emirleri için DataTable instance'ı. */
let assignedWorkOrdersDataTable = null;
/** @type {jQuery|null} Personel listesi için DataTable instance'ı. */
let personnelDataTable = null;
/** @type {jQuery|null} Takım listesi için DataTable instance'ı. */
let teamsDataTable = null;

/** @type {object} Devam eden API isteklerini takip etmek için kullanılır (özellikle buton bazlı). Anahtar: buton ID'si, Değer: true. */
let isApiRequestInProgress = {};

/**
 * Tarayıcı çerezlerinden belirtilen isimdeki çerezin değerini alır.
 * @param {string} name Alınacak çerezin adı.
 * @returns {string|null} Çerezin değeri veya bulunamazsa null.
 */
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


// =================================================================================
// HELPER FUNCTIONS
// =================================================================================

/**
 * Genel yükleme spinner'ını gösterir.
 */
function showSpinner() { $('#loadingSpinner').show(); }

/**
 * Genel yükleme spinner'ını gizler (eğer görünürse).
 */
function hideSpinner() {
    if ($('#loadingSpinner').is(':visible')) {
        $('#loadingSpinner').hide();
    }
}


/**
 * API'ye istek yapmak için genel bir yardımcı fonksiyon.
 * @param {string} endpoint API endpoint'i (örn: "work-orders/")
 * @param {string} method HTTP metodu (GET, POST, PUT, DELETE vb.)
 * @param {object|null} data Gönderilecek veri (POST, PUT, PATCH için) veya query parametreleri (GET için)
 * @param {function} successCallback Başarılı yanıt durumunda çağrılacak fonksiyon
 * @param {function} errorCallback Hata durumunda çağrılacak fonksiyon
 * @param {boolean} [showLoading=true] İstek sırasında spinner gösterilip gösterilmeyeceği
 * @param {jQuery|null} [$buttonToDisable=null] İstek sırasında devre dışı bırakılacak jQuery butonu nesnesi
 * @param {string} [originalButtonText="Kaydet"] Buton devre dışı bırakıldığında ve geri alındığında kullanılacak orijinal metin
 */
function makeApiRequest(endpoint, method, data, successCallback, errorCallback, showLoading = true, $buttonToDisable = null, originalButtonText = "Kaydet") {
    // Buton ID'si yoksa, buton metninden bir ID türet. Bu, aynı anda birden fazla isimsiz butonla çalışırken çakışmaları önlemeye yardımcı olur.
    const buttonId = $buttonToDisable ? ($buttonToDisable.attr('id') || $buttonToDisable.text().trim().replace(/\s+/g, '_')) : null;
    
    if (buttonId && isApiRequestInProgress[buttonId]) {
        console.warn(`API isteği (${buttonId} için) zaten devam ediyor. Yenisi yoksayıldı.`);
        return; // Bu buton için zaten bir istek devam ediyorsa yenisini başlatma
    }

    if (showLoading) showSpinner();
    if ($buttonToDisable) {
        if(buttonId) isApiRequestInProgress[buttonId] = true;
        $buttonToDisable.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> İşleniyor...');
    }

    // API endpoint URL'sini oluşturma
    let fullUrl;
    if (endpoint.startsWith(API_APP_BASE_URL) || endpoint.startsWith('/api/')) {
        fullUrl = endpoint;
    } else {
        fullUrl = `${API_APP_BASE_URL}/${endpoint.startsWith('/') ? endpoint.substring(1) : endpoint}`;
    }
    fullUrl = fullUrl.replace(/\/+/g, '/'); // Birden fazla slash'ı tek slash'e indirge

    const requestSettings = {
        url: fullUrl,
        method: method,
        headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
        success: function(response) {
            if (showLoading) hideSpinner();
            if ($buttonToDisable) { 
                $buttonToDisable.prop('disabled', false).html(originalButtonText);
                if(buttonId) delete isApiRequestInProgress[buttonId];
            }
            if (successCallback) successCallback(response);
        },
        error: function(xhr) {
            if (showLoading) hideSpinner();
            if ($buttonToDisable) { 
                $buttonToDisable.prop('disabled', false).html(originalButtonText); 
                if(buttonId) delete isApiRequestInProgress[buttonId];
            }
            let errorMessage = `API isteği başarısız oldu (${xhr.status}).`;
            // Hata mesajını xhr.responseJSON'dan daha detaylı almaya çalış

            if (xhr.responseJSON) {
                if (xhr.responseJSON.detail) { errorMessage = xhr.responseJSON.detail; }
                else if (Array.isArray(xhr.responseJSON)) { errorMessage = xhr.responseJSON.map(err => typeof err === 'object' ? JSON.stringify(err) : err).join(' '); }
                else if (typeof xhr.responseJSON === 'object') { 
                    errorMessage = Object.entries(xhr.responseJSON).map(([key, value]) => {
                        let fieldError = Array.isArray(value) ? value.join(', ') : value;
                        return `${key !== 'non_field_errors' ? `${key}: ${fieldError}` : fieldError}`; 
                    }).join('\n');
                }
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

    // POST, PUT, PATCH istekleri için data'yı JSON olarak ayarla
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        requestSettings.data = JSON.stringify(data);
        requestSettings.contentType = 'application/json; charset=utf-8';
    } else if (data && method === 'GET') {
        requestSettings.data = data;
    }
    $.ajax(requestSettings);
}

// =================================================================================
// AUTHENTICATION & USER SESSION MANAGEMENT
// =================================================================================

/**
 * Giriş formu gönderildiğinde çalışır. API_LOGIN_URL'e istek yapar.
 * @param {Event} event Form submit olayı.
 */
function handleLoginSubmit(event) {
    event.preventDefault();
    const $button = $('#loginButton');
    const originalButtonText = $button.html();
    const username = $('#username').val();
    const password = $('#password').val();
    $('#loginError').text('');
    
    // Butonu manuel olarak devre dışı bırak ve spinner göster, çünkü bu fonksiyon makeApiRequest kullanmıyor, doğrudan $.ajax kullanıyor.
    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Giriş Yapılıyor...');
 
    $.ajax({
        url: API_LOGIN_URL,
        method: 'POST',
        data: { username: username, password: password },
        success: function(response) {
            authToken = response.token;
            localStorage.setItem('authToken', authToken);
            fetchCurrentUserInfoAndRedirect($button, originalButtonText); 
        },
        error: function(xhr) {
            $button.prop('disabled', false).html(originalButtonText); 
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

/**
 * Mevcut kullanıcı bilgilerini API_USER_ME_URL'den çeker ve başarılı olursa yönlendirme yapar.
 * @param {jQuery|null} [$button=null] Devre dışı bırakılacak buton (opsiyonel, genellikle giriş butonu).
 * @param {string} [originalButtonText="Giriş Yap"] Butonun orijinal metni.
 */
function fetchCurrentUserInfoAndRedirect($button = null, originalButtonText = "Giriş Yap") {
    if (!authToken) {
        if ($button) { $button.prop('disabled', false).html(originalButtonText); }
        if (window.location.pathname !== LOGIN_PAGE_URL) {
            window.location.href = LOGIN_PAGE_URL + "?next=" + encodeURIComponent(window.location.pathname + window.location.search);
        }
        return;
    }
    makeApiRequest(API_USER_ME_URL, 'GET', null,
        function(response) { // successCallback
            currentUser = response;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            const nextUrlParams = new URLSearchParams(window.location.search).get('next');
            window.location.href = nextUrlParams || DASHBOARD_URL; 
        },
        function(errorMessage) { // errorCallback
            authToken = null; currentUser = null;
            localStorage.removeItem('authToken'); localStorage.removeItem('currentUser');
            if ($('#loginError').length) {
                 $('#loginError').text('Oturum bilgileri alınamadı veya token geçersiz. Lütfen tekrar giriş yapın.');
            } else if (window.location.pathname !== LOGIN_PAGE_URL) {
                window.location.href = LOGIN_PAGE_URL;
            }
        },
        true, // showLoading
        $button, // $buttonToDisable
        originalButtonText // originalButtonText
    );
}

/**
 * Kullanıcı oturumunu sonlandırır ve giriş sayfasına yönlendirir.
 */
function handleLogout() {
    authToken = null; currentUser = null;
    localStorage.removeItem('authToken'); localStorage.removeItem('currentUser');
    window.location.href = LOGIN_PAGE_URL;
}

// =================================================================================
// UI MANAGEMENT & NAVIGATION
// =================================================================================

/**
 * Kullanıcı bilgilerini ve rollerini arayüzde günceller.
 * Eğer `currentUser` global değişkeni boşsa API'den çekmeye çalışır.
 */
function updateUserInfoDisplayAndMenus() {
    if (!currentUser && authToken) { // Kullanıcı bilgisi yok ama token var ise API'den çek
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

/**
 * Mevcut kullanıcı bilgilerine göre arayüzdeki menüleri ve içerik görünürlüğünü ayarlar.
 * `.user-role-menu` ve `.user-role-content` class'larına sahip elementleri yönetir.
 */
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

    // Kullanıcı rolüne göre menü ve içerik gösterimi
    if (!window.location.hash && $('.page-content.active').length === 0) {
        const firstVisibleMenuTarget = $('.user-role-menu:visible').first().find('.page-link').data('target') || 'dashboardContent';
        loadContent(firstVisibleMenuTarget);
    }
}

/**
 * İlgili içerik bölümünü yükler ve gösterir, sidebar'daki linki aktif hale getirir.
 * URL hash'ini günceller ve içerik ID'sine göre ilgili veri yükleme fonksiyonlarını çağırır.
 * @param {string} contentId Gösterilecek içerik bölümünün ID'si (örn: "workOrdersContent").
 */
function loadContent(contentId) {
    if (!contentId) contentId = 'dashboardContent';
    $('.page-content').removeClass('active').hide();
    $('#' + contentId).addClass('active').show();
    $('.sidebar .nav-link.page-link').removeClass('active');
    $(`.sidebar .nav-link.page-link[data-target="${contentId}"]`).addClass('active');

    // URL hash'ini güncelle (tarayıcı geçmişi için)
    if (contentId !== 'dashboardContent') { window.location.hash = contentId.replace('Content', ''); }
    else { history.pushState("", document.title, window.location.pathname + window.location.search); }
    
    // Ana panel yükleniyorsa stok uyarılarını göster
    if (contentId === 'dashboardContent') { displayDashboardStockWarningsFromStockLevelsAPI(); }
    
    // İçerik ID'sine göre ilgili verileri yükleme fonksiyonlarını çağır
    if (contentId === 'workOrdersContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchWorkOrders(); populateWorkOrderFormDropdowns(); }
    else if (contentId === 'stockLevelsContent') { fetchStockLevels(); }
    else if (contentId === 'aircraftsContent' && (currentUser?.is_staff || currentUser?.is_superuser || currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM')) { 
        populateAircraftFilters();
        fetchAircrafts(); 
    }
    else if (contentId === 'partsContent' && (currentUser?.is_staff || currentUser?.is_superuser || currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM')) { 
        populateAdminPartFilters();
        fetchParts();
    }
    else if (contentId === 'assignedWorkOrdersContent' && currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM') { fetchAssignedWorkOrders(); }
    else if (contentId === 'assembleAircraftContent' && currentUser?.personnel_profile?.team_type === 'ASSEMBLY_TEAM') { populateAssembleAircraftFormDropdowns(); }
    else if (contentId === 'producePartContent' && currentUser?.personnel_profile && ['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(currentUser.personnel_profile.team_type)) { populateProducePartFormDropdowns(); }
    else if (contentId === 'myTeamPartsContent' && currentUser?.personnel_profile && ['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(currentUser.personnel_profile.team_type)) { 
        populateMyTeamPartFilters(); // Üretimci için parça filtreleri
        fetchMyTeamParts();
    } else if (contentId === 'personnelContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchPersonnel(); }
    else if (contentId === 'teamsContent' && (currentUser?.is_staff || currentUser?.is_superuser)) { fetchTeams();
    }
}

// =================================================================================
// DATA FETCHING & DATATABLE INITIALIZATION
// =================================================================================

/**
 * İş emirlerini API'den (`work-orders/`) çekerek DataTables ile listeler.
 * Sunucu tarafı (server-side) işleme, sıralama, arama ve filtreleme özelliklerini destekler.
 * Sadece Admin/Staff kullanıcıları için çalışır.
 */
function fetchWorkOrders() {
    const workOrderTableElement = $('#workOrdersTable');
    $('#workOrderAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') {
        console.error("DataTables JS kütüphanesi yüklenmemiş!");
        $('#workOrderAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>');
        return;
    }

    if ($.fn.DataTable.isDataTable(workOrderTableElement)) {
        workOrdersDataTable.ajax.reload(); // DataTable zaten başlatılmışsa, sadece verileri yeniden yükle. Filtreler vb. ajax.data içinden gelecek.
        return;
    }
    
    console.info("WorkOrders DataTable başlatılıyor...");
    workOrdersDataTable = workOrderTableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}work-orders/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) {
                const drfParams = { 
                    length: d.length === -1 ? 999999 : d.length,
                    start: d.start,
                    draw: d.draw 
                };
                if (d.search && d.search.value) {
                    drfParams.search = d.search.value;
                }
                if (d.order && d.order.length > 0) {
                    const orderColumnIndex = d.order[0].column;
                    const orderDirection = d.order[0].dir;
                    let orderColumnName = d.columns[orderColumnIndex].data; 
                    const orderingFieldMap = { 
                        'aircraft_model_name': 'aircraft_model__name',
                        'status_display': 'status',
                        'assigned_to_assembly_team_name': 'assigned_to_assembly_team__name',
                        'created_by_username': 'created_by__username'
                    };
                    let sortableFieldName = orderingFieldMap[orderColumnName] || orderColumnName;
                    if (sortableFieldName) {
                        drfParams.ordering = (orderDirection === 'desc' ? '-' : '') + sortableFieldName;
                    }
                }
                // Durum filtresini ekle
                const statusFilterValue = $('#workOrderStatusFilter').val();
                if (statusFilterValue) {
                    drfParams.status = statusFilterValue;
                }
                return drfParams;
            },
            error: function (xhr, error, thrown) {
                hideSpinner(); 
                let errorMsg = "İş emirleri DataTable ile yüklenirken bir hata oluştu.";
                if (xhr.responseJSON && xhr.responseJSON.detail) { errorMsg = xhr.responseJSON.detail;}
                else if (xhr.status === 403) { errorMsg = "İş emirlerini görüntüleme yetkiniz yok.";}
                else if (xhr.status === 404) { errorMsg = "İş emri API endpoint'i bulunamadı.";}
                else if (xhr.responseJSON) { errorMsg = JSON.stringify(xhr.responseJSON); }
                $('#workOrderAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
                console.error("DataTable Ajax Error:", xhr.status, errorMsg, xhr.responseText);
            }
        },
        columns: [
            { data: "id", title: "ID", width: "5%" },
            { data: "aircraft_model_name", title: "Uçak Modeli", defaultContent: "-" },
            { data: "quantity", title: "Miktar" },
            {  
                data: "status_display", title: "Durum", 
                render: function(data, type, row) { 
                    let badgeClass = 'bg-light text-dark'; 
                    if (row.status === 'PENDING') badgeClass = 'bg-warning text-dark';
                    else if (row.status === 'ASSIGNED') badgeClass = 'bg-primary text-white';
                    else if (row.status === 'IN_PROGRESS') badgeClass = 'bg-info text-dark';
                    else if (row.status === 'COMPLETED') badgeClass = 'bg-success text-white';
                    else if (row.status === 'CANCELLED') badgeClass = 'bg-danger text-white';
                    return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
                }
            },
            { data: "assigned_to_assembly_team_name", title: "Atanan Takım", defaultContent: "-" },
            { data: "created_by_username", title: "Oluşturan", defaultContent: "-" },
            { 
                data: "created_at", title: "Oluşturma Tarihi",
                render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }
            },
            {
                data: null, title: "İşlemler", orderable: false, searchable: false,
                render: function (data, type, row) {
                    let buttons = '';
                    if (currentUser && (currentUser.is_staff || currentUser.is_superuser)) {
                        buttons += `<button class="btn btn-sm btn-warning btn-edit-wo me-1" data-id="${row.id}" data-bs-toggle="modal" data-bs-target="#newWorkOrderModal" title="Düzenle"><i class="fas fa-edit"></i></button> `;
                        if (row.status !== 'CANCELLED' && row.status !== 'COMPLETED') {
                             buttons += `<button class="btn btn-sm btn-danger btn-delete-wo" data-id="${row.id}" title="İptal Et"><i class="fas fa-trash-alt"></i></button>`;
                        }
                    }
                    return buttons || '-';
                }
            }
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true,
        pageLength: 10,
        lengthMenu: [ [10, 25, 50, 100, -1], [10, 25, 50, 100, "Tümü"] ], // "Tümü" seçeneği eklendi
    });
}

/**
 * Tüm parçaları API'den (`parts/`) çekerek DataTables ile listeler.
 * Admin ve Montajcılar için kullanılır. Sunucu tarafı işleme, sıralama, arama ve filtreleme destekler.
 */
function fetchParts() {
    const partTableElement = $('#adminPartsTable');
    $('#adminPartsAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') { console.error("DataTables JS kütüphanesi yüklenmemiş!"); $('#adminPartsAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>'); return; }
    if ($.fn.DataTable.isDataTable(partTableElement)) { adminPartsDataTable.ajax.reload(); return; }
    
    console.log("Initializing Admin Parts DataTable...");
    adminPartsDataTable = partTableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}parts/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) {
                let drfParams = {
                    length: d.length === -1 ? 99999 : d.length,
                    start: d.start,
                    draw: d.draw
                };
                if (d.search && d.search.value) { drfParams.search = d.search.value; }
                if (d.order && d.order.length > 0) {
                    const colIndex = d.order[0].column;
                    const colDir = d.order[0].dir;
                    const colName = d.columns[colIndex].data;
                    const fieldMap = {
                        'part_type_display': 'part_type__category',
                        'aircraft_model_compatibility_name': 'aircraft_model_compatibility__name',
                        'produced_by_team_name': 'produced_by_team__name',
                        'created_by_personnel_username': 'created_by_personnel__user__username',
                        'status_display': 'status',
                        'installed_aircraft_info': null // Bu alana göre sıralama desteklenmeyebilir
                    };
                    let sortableField = fieldMap[colName] || colName;
                    if (sortableField) drfParams.ordering = (colDir === 'desc' ? '-' : '') + sortableField;
                }
                // Parça filtrelerini ekle (durum, kategori, uçak modeli)
                if ($('#adminPartStatusFilter').val()) drfParams.status = $('#adminPartStatusFilter').val();
                if ($('#adminPartCategoryFilter').val()) drfParams.part_type = $('#adminPartCategoryFilter').val(); // PartType ID'si
                if ($('#adminPartAircraftModelFilter').val()) drfParams.aircraft_model_compatibility = $('#adminPartAircraftModelFilter').val();
                return drfParams;
            },
            error: function (xhr) { 
                hideSpinner();
                let errorMsg = "Parçalar DataTable ile yüklenirken bir hata oluştu.";
                if (xhr.responseJSON && xhr.responseJSON.detail) { errorMsg = xhr.responseJSON.detail;}
                else if (xhr.status === 403) { errorMsg = "Parçaları görüntüleme yetkiniz yok.";}
                else if (xhr.responseJSON) { errorMsg = JSON.stringify(xhr.responseJSON); }
                $('#adminPartsAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
            }
        },
        columns: [
            { data: "id", title: "ID" },
            { data: "serial_number", title: "Seri No" },
            { data: "part_type_display", title: "Parça Tipi", defaultContent: "-" },
            { data: "aircraft_model_compatibility_name", title: "Uyumlu Model", defaultContent: "-" },
            { data: "status_display", title: "Durum", render: function(data, type, row){ /* badge render */ 
                let badgeClass = 'bg-light text-dark'; 
                if (row.status === 'AVAILABLE') badgeClass = 'bg-success text-white';
                else if (row.status === 'USED') badgeClass = 'bg-secondary text-white';
                else if (row.status === 'IN_PRODUCTION') badgeClass = 'bg-info text-dark';
                else if (row.status === 'DEFECTIVE') badgeClass = 'bg-danger text-white';
                else if (row.status === 'RECYCLED') badgeClass = 'bg-dark text-white';
                return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
            }},
            { data: "produced_by_team_name", title: "Üreten Takım", defaultContent: "-" },
            { data: "created_by_personnel_username", title: "Üreten Personel", defaultContent: "-" },
            { data: "production_date", title: "Üretim Tarihi", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            { data: "installed_aircraft_info", title: "Takılı Olduğu Uçak", defaultContent: "-"},
            {
                data: null, title: "İşlemler", orderable: false, searchable: false,
                render: function (data, type, row) {
                    let buttons = '';                    
                    // Admin ve Montajcı tüm parçaları geri dönüştürebilir.
                    const canRecycle = currentUser && (currentUser.is_staff || currentUser.is_superuser || (currentUser.personnel_profile && currentUser.personnel_profile.team_type === 'ASSEMBLY_TEAM'));

                    if (canRecycle && row.status !== 'RECYCLED' && row.status !== 'USED') {
                         buttons += `<button class="btn btn-sm btn-outline-danger btn-recycle-part" data-id="${row.id}" title="Geri Dönüştür"><i class="fas fa-recycle"></i></button>`;
                    }
                    return buttons || '-';
                }
            }
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}

/**
 * Üretimci personelin kendi takımının ürettiği parçaları API'den (`parts/`) çekerek DataTables ile listeler.
 * Backend, isteği yapan kullanıcıya göre filtreleme yapar. Sunucu tarafı işleme destekler.
 */
function fetchMyTeamParts() { // Üretimci için kendi takımının parçaları
    const partTableElement = $('#myTeamPartsTable');
    $('#myTeamPartsAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') { console.error("DataTables JS kütüphanesi yüklenmemiş!"); $('#myTeamPartsAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>'); return; }
    if ($.fn.DataTable.isDataTable(partTableElement)) { myTeamPartsDataTable.ajax.reload(); return; }

    console.log("Initializing My Team Parts DataTable...");
    myTeamPartsDataTable = partTableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}parts/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) {
                let drfParams = {
                    length: d.length === -1 ? 10000 : d.length,
                    start: d.start,
                    draw: d.draw
                };
                if (d.search && d.search.value) { drfParams.search = d.search.value; }
                if (d.order && d.order.length > 0) { 
                    const colIndex = d.order[0].column;
                    const colDir = d.order[0].dir;
                    const colName = d.columns[colIndex].data;
                     const fieldMap = {
                        'aircraft_model_compatibility_name': 'aircraft_model_compatibility__name',
                        'status_display': 'status',
                    };
                    let sortableField = fieldMap[colName] || colName;
                    if (sortableField) drfParams.ordering = (colDir === 'desc' ? '-' : '') + sortableField;
                }
                // Filtreleri ekle
                if ($('#producerPartStatusFilter').val()) drfParams.status = $('#producerPartStatusFilter').val();
                if ($('#producerPartAircraftModelFilter').val()) drfParams.aircraft_model_compatibility = $('#producerPartAircraftModelFilter').val();
                return drfParams;
            },
            error: function (xhr) { 
                hideSpinner();
                let errorMsg = "Takım parçaları yüklenirken hata oluştu."; /* ... (detaylı hata mesajı) ... */
                $('#myTeamPartsAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
            }
        },
        columns: [ 
            { data: "id", title: "ID" },
            { data: "serial_number", title: "Seri No" },
            { data: "aircraft_model_compatibility_name", title: "Uyumlu Model", defaultContent: "-" },
            { data: "status_display", title: "Durum", render: function(data, type, row){ /* badge render */ 
                let badgeClass = 'bg-light text-dark'; 
                if (row.status === 'AVAILABLE') badgeClass = 'bg-success text-white';
                else if (row.status === 'USED') badgeClass = 'bg-secondary text-white';
                else if (row.status === 'IN_PRODUCTION') badgeClass = 'bg-info text-dark';
                else if (row.status === 'DEFECTIVE') badgeClass = 'bg-danger text-white';
                else if (row.status === 'RECYCLED') badgeClass = 'bg-dark text-white';
                return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
            }},
            { data: "production_date", title: "Üretim Tarihi", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            { data: "installed_aircraft_info", title: "Takılı Olduğu Uçak", defaultContent: "-"},
            {
                data: null, title: "İşlemler", orderable: false, searchable: false,
                render: function (data, type, row) {
                    let buttons = '';
                    // Üretimci sadece kendi takımının ürettiği ve uygun durumdaki parçaları geri dönüştürebilir.
                    // Backend zaten IsOwnerTeamOrAdminForPart ile bunu kontrol ediyor.
                    if (row.status !== 'RECYCLED' && row.status !== 'USED') { 
                         buttons += `<button class="btn btn-sm btn-outline-danger btn-recycle-part" data-id="${row.id}" title="Geri Dönüştür"><i class="fas fa-recycle"></i></button>`;
                    }
                    return buttons || '-';
                }
            }
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}

/**
 * Hava araçlarını API'den (`aircraft/`) çekerek DataTables ile listeler.
 * Admin, Staff ve Montajcılar için kullanılır. Sunucu tarafı işleme, sıralama, arama ve filtreleme destekler.
 */
function fetchAircrafts() {
    const aircraftTableElement = $('#aircraftsTable');
    $('#aircraftsAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') { console.error("DataTables JS kütüphanesi yüklenmemiş!"); $('#aircraftsAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>'); return; }
    if ($.fn.DataTable.isDataTable(aircraftTableElement)) { aircraftsDataTable.ajax.reload(); return; }

    console.log("Initializing Aircrafts DataTable...");
    aircraftsDataTable = aircraftTableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}aircraft/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) {
                let drfParams = {
                    length: d.length === -1 ? 99999 : d.length,
                    start: d.start,
                    draw: d.draw
                };
                if (d.search && d.search.value) { drfParams.search = d.search.value; }
                if (d.order && d.order.length > 0) {
                    const colIndex = d.order[0].column;
                    const colDir = d.order[0].dir;
                    const colName = d.columns[colIndex].data;
                    const fieldMap = {
                        'aircraft_model_name': 'aircraft_model__name',
                        'status_display': 'status',
                        'assembled_by_team_name': 'assembled_by_team__name',
                        'work_order_id_display': 'work_order__id'
                    };
                    let sortableField = fieldMap[colName] || colName;
                    if (sortableField) drfParams.ordering = (colDir === 'desc' ? '-' : '') + sortableField;
                }
                // Hava aracı filtrelerini ekle (durum, model, takım)
                if ($('#aircraftStatusFilter').val()) drfParams.status = $('#aircraftStatusFilter').val();
                if ($('#aircraftModelFilter').val()) drfParams.aircraft_model = $('#aircraftModelFilter').val();
                if (currentUser && (currentUser.is_staff || currentUser.is_superuser) && $('#aircraftTeamFilter').val()) {
                    drfParams.assembled_by_team = $('#aircraftTeamFilter').val();
                }
                return drfParams;
            },
            error: function (xhr) {
                hideSpinner();
                let errorMsg = "Uçaklar yüklenirken hata oluştu."; 
                $('#aircraftsAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
            }
        },
        columns: [
            { data: "id", title: "ID" },
            { data: "serial_number", title: "Seri No" },
            { data: "aircraft_model_name", title: "Uçak Modeli", defaultContent: "-" },
            { 
                data: "status_display", title: "Durum",
                render: function(data, type, row) {
                    let badgeClass = 'bg-light text-dark';
                    if (row.status === 'ACTIVE') badgeClass = 'bg-success text-white';
                    else if (row.status === 'READY_FOR_DELIVERY') badgeClass = 'bg-info text-dark';
                    else if (row.status === 'DELIVERED') badgeClass = 'bg-primary text-white';
                    else if (row.status === 'DECOMMISSIONED') badgeClass = 'bg-warning text-dark';
                    else if (row.status === 'RECYCLED') badgeClass = 'bg-secondary text-white';
                    return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
                }
            },
            { data: "assembled_by_team_name", title: "Montaj Takımı", defaultContent: "-" },
            { data: "assembly_date", title: "Montaj Tarihi", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            { data: "work_order_id_display", title: "İş Emri ID", defaultContent: "-", render: function(data, type, row){ return row.work_order || '-';}},
            {// İşlem butonları (Geri Dönüştür)
                data: null, title: "İşlemler", orderable: false, searchable: false,
                render: function (data, type, row) {
                    let buttons = '';
                    // Admin ve uçağı monte eden takımın üyesi geri dönüştürebilir.
                    const canRecycle = currentUser && 
                                       (currentUser.is_staff || currentUser.is_superuser || 
                                        (currentUser.personnel_profile && // Kullanıcının personel profili var mı?
                                         currentUser.personnel_profile.team_id === row.assembled_by_team && // Takım ID'leri eşleşiyor mu? (row.assembled_by_team ID olmalı)
                                         currentUser.personnel_profile.team_type === 'ASSEMBLY_TEAM'));

                    if (canRecycle && row.status !== 'RECYCLED') {
                        buttons += `<button class="btn btn-sm btn-outline-danger btn-recycle-aircraft" data-id="${row.id}" title="Geri Dönüştür"><i class="fas fa-recycle"></i></button>`;
                    }
                    return buttons || '-';
                }
            }
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}




/**
 * Verilen uçak modellerini kullanarak bir model seçici (radyo butonları veya dropdown) oluşturur.
 * @param {string} containerId Seçicinin yerleştirileceği HTML elementinin ID'si.
 * @param {Array|object} modelsData Uçak modellerini içeren dizi veya {data: []} formatında nesne.
 * @param {string} inputRadioName Radyo butonları için 'name' attribute'u veya select için 'name' attribute'u.
 * @param {boolean} [isRadio=false] Radyo butonları mı (true) yoksa dropdown mı (false) oluşturulacağı.
 * @param {string|number|null} [selectedValue=null] Önceden seçili olacak modelin ID'si.
 */
function createAircraftModelSelector(containerId, modelsData, inputRadioName, isRadio = false, selectedValue = null) {
    const container = $(`#${containerId}`);
    container.empty();

    const models = Array.isArray(modelsData) ? modelsData : (modelsData?.data && Array.isArray(modelsData.data) ? modelsData.data : []);

    if (!models || models.length === 0) {
        container.append('<p class="text-muted small mt-1">Uygun uçak modeli bulunamadı.</p>');
        return;
    }

    if (isRadio) {
        container.addClass('row g-2 aircraft-model-selector-grid'); 
        models.forEach(model => {
            const isChecked = model.id == selectedValue ? 'checked' : '';
            const uniqueRadioId = `${inputRadioName}_${model.id}`;

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

/**
 * Yeni iş emri veya iş emri düzenleme formu için dropdown'ları (uçak modelleri, montaj takımları) doldurur.
 * @param {object|null} [editData=null] Düzenleme modunda ise, mevcut iş emri verileri.
 */
function populateWorkOrderFormDropdowns(editData = null) {
    // Uçak Modelleri (Görsel Seçici)
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.data || [];;
        createAircraftModelSelector('woAircraftModelContainer', models, 'wo_aircraft_model', true, editData ? editData.aircraft_model : null);
    });

    // Montaj Takımları (Dropdown)
    makeApiRequest(`teams/?team_type=ASSEMBLY_TEAM`, 'GET', null, function(teamsResponse) {
        const teams = teamsResponse.data || [];
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
        // Model seçici zaten populateWorkOrderFormDropdowns içinde editData null ise sıfırlanır.
    }
}

// =================================================================================
// FORM SUBMISSION HANDLERS
// =================================================================================

/**
 * Yeni bir iş emri oluşturur (POST `work-orders/`) veya mevcut bir iş emrini günceller (PUT `work-orders/{id}/`).
 * @param {string|number|null} [workOrderId=null] Güncellenecek iş emrinin ID'si. Yoksa yeni oluşturulur.
 * @param {jQuery} $triggerButton İsteği tetikleyen buton (devre dışı bırakma ve metin güncelleme için).
 */
function saveWorkOrder(workOrderId = null, $triggerButton) {
    const originalButtonText = $triggerButton.html(); // Buton metnini al
    const formData = {
        aircraft_model: $('input[name="wo_aircraft_model"]:checked').val(),
        quantity: parseInt($('#woQuantity').val()),
        assigned_to_assembly_team: $('#woAssignedTeam').val() || null,
        target_completion_date: $('#woTargetDate').val() || null,
        notes: $('#woNotes').val()
    };

    if (!formData.aircraft_model) {
        $('#newWorkOrderError').text("Lütfen bir uçak modeli seçin."); return;
    }
    if (!formData.quantity || formData.quantity < 1) {
        $('#newWorkOrderError').text("Lütfen geçerli bir miktar girin."); return;
    }
    $('#newWorkOrderError').text("");

    const method = workOrderId ? 'PUT' : 'POST';
    const endpoint = workOrderId ? `work-orders/${workOrderId}/` : `work-orders/`;

    makeApiRequest(endpoint, method, formData,
        function(response) {
            $('#newWorkOrderModal').modal('hide');
            $('#workOrderAlerts').html(`<div class="alert alert-success alert-dismissible fade show" role="alert">İş emri başarıyla ${workOrderId ? 'güncellendi' : 'oluşturuldu'}.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`);
            if (workOrdersDataTable) { workOrdersDataTable.ajax.reload(null, false); }
        },
        function(errorMsg, xhr) {
            let displayError = errorMsg;
            // xhr.responseJSON içindeki hataları daha iyi formatlayabiliriz
            if (xhr.responseJSON) {
                displayError = Object.entries(xhr.responseJSON).map(([key, value]) => `${key !== 'non_field_errors' ? (key + ': ') : ''}${Array.isArray(value) ? value.join(', ') : value}`).join('; ');
            }
            $('#newWorkOrderError').text(displayError);
        },
        true, $triggerButton, originalButtonText
    );
}

// =================================================================================
// ACTION HANDLERS (DELETE, RECYCLE, ETC.)
// =================================================================================

/**
 * Belirtilen ID'ye sahip iş emrini iptal eder (DELETE `work-orders/{id}/`).
 * Kullanıcıdan onay alır.
 * @param {string|number} workOrderId İptal edilecek iş emrinin ID'si.
 */
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

// =================================================================================
// DASHBOARD & STOCK MANAGEMENT
// =================================================================================

/**
 * Stok seviyelerini (parça ve uçak stokları) API'den (`inventory/stock-levels/`) çeker ve DataTables ile görüntüler.
 * Parça stokları herkes için, uçak stokları Admin/Staff/Montajcı için gösterilir.
 */
function fetchStockLevels() {
    // Parça Stokları DataTable
    const partStockTableElement = $('#partStockTable');
    if ($.fn.DataTable.isDataTable(partStockTableElement)) { partStockTableElement.DataTable().ajax.reload(); } 
    else {
        partStockTableElement.DataTable({
            processing: true, serverSide: true,
            ajax: {
                url: `${API_APP_BASE_URL}inventory/stock-levels/`,
                type: "GET",
                headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
                data: function (d) {
                    d.stock_type = 'parts';
                    return d;
                },
                error: function (xhr) { $('#partStockAlerts').html(`<div class="alert alert-danger">Parça stokları yüklenemedi: ${xhr.responseText}</div>`); }
            },
            columns: [
                { data: "aircraft_model_name", title: "Uçak Modeli" },
                { data: "part_type_category_display", title: "Parça Tipi" },
                { data: "AVAILABLE", title: "Mevcut" },
                { data: "USED", title: "Kullanıldı" },
                { data: "RECYCLED", title: "Geri Dönüştürülmüş" },
                { 
                    data: "warning_zero_stock", title: "Uyarı",
                    render: function(data) { return data ? '<span class="badge bg-danger">Stok Yok</span>' : '<span class="badge bg-success">Yeterli</span>'; }
                }
            ],
            order: [[0, 'asc'], [1, 'asc']], language: { url: DATATABLES_TR_JSON_URL }, responsive: true, 
            pageLength: -1,
            lengthChange: false,
            searching: false,
        });
    }

    // Uçak Stokları DataTable (Sadece Admin ve Montajcı görür)
    if (currentUser && (currentUser.is_staff || currentUser.is_superuser || (currentUser.personnel_profile && currentUser.personnel_profile.team_type === 'ASSEMBLY_TEAM'))) {
        $('#aircraftStockContainer').show();
        const aircraftStockTableElement = $('#aircraftStockTable');
        if ($.fn.DataTable.isDataTable(aircraftStockTableElement)) { aircraftStockTableElement.DataTable().ajax.reload(); }
        else {
            aircraftStockTableElement.DataTable({
                processing: true, serverSide: true,
                ajax: {
                    url: `${API_APP_BASE_URL}inventory/stock-levels/`,
                    type: "GET",
                    headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
                    data: function (d) {
                        d.stock_type = 'aircrafts';
                        return d;
                    },
                    error: function (xhr) { $('#aircraftStockAlerts').html(`<div class="alert alert-danger">Uçak stokları yüklenemedi: ${xhr.responseText}</div>`); }
                },
                columns: [
                    { data: "aircraft_model_name", title: "Uçak Modeli" },
                    { data: "AVAILABLE", title: "Hazır (Aktif)" },
                    { data: "SOLD", title: "Satıldı" },
                    { data: "MAINTENANCE", title: "Bakımda" },
                    { data: "RECYCLED", title: "Geri Dönüştürülmüş" }
                ],
                order: [[0, 'asc']], language: { url: DATATABLES_TR_JSON_URL }, responsive: true, 
                pageLength: -1,
                lengthChange: false,
                searching: false, 
            });
        }
    } else {
        $('#aircraftStockContainer').hide();
    }
}

// =================================================================================
// FORM POPULATION (SPECIFIC FORMS)
// =================================================================================

/**
 * "Uçak Montaj" formu için gerekli alanları (uçak modelleri, uygun iş emirleri) API'den çekerek doldurur.
 */
function populateAssembleAircraftFormDropdowns() {
    // Uçak Modelleri (Görsel Seçici)
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.data || []; 
        createAircraftModelSelector('assembleAircraftModelContainer', models, 'assemble_aircraft_model_radio', true);
    });

    // Uygun İş Emirleri (Dropdown)
    makeApiRequest(`work-orders/`, 'GET', { status: 'PENDING,ASSIGNED,IN_PROGRESS' }, function(ordersResponse) {
        const orders = ordersResponse.data || []; 
        const select = $('#assembleWorkOrder'); 
        select.empty().append('<option value="">İş Emri Seçiniz</option>');
        if (Array.isArray(orders)) {
            orders.forEach(order => {
                select.append(`<option value="${order.id}">#${order.id} - ${order.aircraft_model_name} (${order.quantity} adet) - Durum: ${order.status_display}</option>`);
            });
        }
    });
}

function populateMyTeamPartFilters() {
    // Uçak Modelleri
    makeApiRequest('aircraft-models/', 'GET', null, function(response) {
        const models = response.data || response;
        const select = $('#producerPartAircraftModelFilter');
        select.empty().append('<option value="">Tüm Uçak Modelleri</option>');
        if(Array.isArray(models)) {
            models.forEach(model => {
                select.append(`<option value="${model.id}">${model.name_display}</option>`);
            });
        }
    });
}

function populateAdminPartFilters() {
    // Parça Kategorileri
    makeApiRequest('part-types/', 'GET', null, function(response) {
        const categories = response.data || response;
        const select = $('#adminPartCategoryFilter');
        select.empty().append('<option value="">Tüm Kategoriler</option>');
        if(Array.isArray(categories)) {
            categories.forEach(cat => {
                select.append(`<option value="${cat.id}">${cat.category_display}</option>`);
            });
        }
    });
    // Uçak Modelleri
    makeApiRequest('aircraft-models/', 'GET', null, function(response) {
        const models = response.data || response;
        const select = $('#adminPartAircraftModelFilter');
        select.empty().append('<option value="">Tüm Uçak Modelleri</option>');
        if(Array.isArray(models)) {
            models.forEach(model => {
                select.append(`<option value="${model.id}">${model.name_display}</option>`);
            });
        }
    });
}

function populateAircraftFilters() {
    // Uçak Modelleri
    makeApiRequest('aircraft-models/', 'GET', null, function(response) {
        const models = response.data || response;
        const select = $('#aircraftModelFilter');
        select.empty().append('<option value="">Tüm Uçak Modelleri</option>');
        if(Array.isArray(models)) {
            models.forEach(model => {
                select.append(`<option value="${model.id}">${model.name_display}</option>`);
            });
        }
    });
    // Montaj Takımları (Sadece Admin/Staff için)
    if (currentUser && (currentUser.is_staff || currentUser.is_superuser)) {
        makeApiRequest('teams/?team_type=ASSEMBLY_TEAM', 'GET', null, function(response) {
            const teams = response.data || response;
            const select = $('#aircraftTeamFilter');
            select.empty().append('<option value="">Tüm Montaj Takımları</option>');
            if(Array.isArray(teams)) {
                teams.forEach(team => {
                    select.append(`<option value="${team.id}">${team.name}</option>`);
                });
            }
        });
    }
}

/**
 * "Uçak Montaj" formunun gönderilmesini yönetir.
 * API'ye (`assembly/assemble-aircraft/`) POST isteği yapar.
 * @param {Event} event Form submit olayı.
 */
function handleAssembleAircraftFormSubmit(event) {
    event.preventDefault();
    const $form = $(this);
    const $button = $form.find('button[type="submit"]');
    const originalButtonText = $button.html();

    const formData = {
        aircraft_model_id: parseInt($form.find('input[name="assemble_aircraft_model_radio"]:checked').val()),
        work_order_id: $form.find('#assembleWorkOrder').val() ? parseInt($form.find('#assembleWorkOrder').val()) : null
    };

    if (!formData.aircraft_model_id) {
        $('#assembleAircraftAlerts').html('<div class="alert alert-danger">Lütfen bir uçak modeli seçin.</div>').show();
        return;
    }
    $('#assembleAircraftAlerts').empty().hide();

    makeApiRequest('assembly/assemble-aircraft/', 'POST', formData,
        function(response) {
            $('#assembleAircraftAlerts').html(`<div class="alert alert-success">Uçak başarıyla monte edildi! Seri No: ${response.serial_number}</div>`).show();
            $form[0].reset();
            $form.find('input[name="assemble_aircraft_model_radio"]').prop('checked', false).closest('.aircraft-model-card').removeClass('selected');
            if ($('#stockLevelsContent').is(':visible')) fetchStockLevels();
            if ($('#aircraftsContent').is(':visible')) fetchAircrafts();
        }, // Hata durumunda gösterilecek mesaj için errorCallback
        function(errorMsg, xhr) {
            let detailedError = "Montaj sırasında bir hata oluştu.";
            if (xhr.responseJSON) {
                if (xhr.responseJSON.error && xhr.responseJSON.missing_parts && Array.isArray(xhr.responseJSON.missing_parts)) {
                    detailedError = `${xhr.responseJSON.error}<br><b>Eksik Parçalar:</b> ${xhr.responseJSON.missing_parts.join(', ')}`;
                } else if (typeof xhr.responseJSON === 'object') {
                    detailedError = Object.entries(xhr.responseJSON).map(([key, value]) => `${key !== 'non_field_errors' ? (key + ': ') : ''}${Array.isArray(value) ? value.join(', ') : value}`).join('; ');
                } else {
                    detailedError = errorMsg; // makeApiRequest'ten gelen genel mesaj
                }
            } else {
                detailedError = errorMsg;
            }
            $('#assembleAircraftAlerts').html(`<div class="alert alert-danger">${detailedError}</div>`).show();
        },
        true, $button, originalButtonText
    );
}

/**
 * "Parça Üretim" formu için uçak modeli seçicisini API'den (`aircraft-models/`) veri çekerek doldurur.
 */
function populateProducePartFormDropdowns() {
    makeApiRequest(`aircraft-models/`, 'GET', null, function(modelsResponse) {
        const models = modelsResponse.data || [];
        // 'produce_part_model_radio' benzersiz input name
        createAircraftModelSelector('producePartAircraftModelContainer', models, 'produce_part_model_radio', true);
    });
}

/**
 * "Parça Üretim" formunun gönderilmesini yönetir.
 * API'ye (`parts/`) POST isteği yapar.
 * @param {Event} event Form submit olayı.
 */
function handleProducePartFormSubmit(event) {
    event.preventDefault();
    const $form = $(this);
    const $button = $form.find('button[type="submit"]');
    const originalButtonText = $button.html();

    const formData = {
        aircraft_model_compatibility: parseInt($form.find('input[name="produce_part_model_radio"]:checked').val())
    };

    if (!formData.aircraft_model_compatibility) {
        $('#producePartAlerts').html('<div class="alert alert-danger">Lütfen uyumlu olacağı bir uçak modeli seçin.</div>').show();
        return;
    }
    $('#producePartAlerts').empty().hide();
    
    makeApiRequest('parts/', 'POST', formData,
        function(response) {
            $('#producePartAlerts').html(`<div class="alert alert-success">Parça başarıyla üretildi! Seri No: ${response.serial_number} (${response.part_type_display} - ${response.aircraft_model_compatibility_name} için)</div>`).show();
            $form[0].reset();
            $form.find('input[name="produce_part_model_radio"]').prop('checked', false).closest('.aircraft-model-card').removeClass('selected');
            if ($('#stockLevelsContent').is(':visible')) fetchStockLevels();
            if ($('#myTeamPartsContent').is(':visible')) fetchMyTeamParts();
        }, // Hata durumunda gösterilecek mesaj için errorCallback
        function(errorMsg, xhr) { // xhr'ı da alalım
            let displayError = errorMsg;
            if (xhr.status === 500) {
                displayError = "Sunucuda bir hata oluştu (Seri No çakışması veya beklenmedik bir sorun). Lütfen daha sonra tekrar deneyin veya sistem yöneticisine başvurun.";
            } else if (xhr.responseJSON) { // Diğer 400 hataları için
                 displayError = Object.entries(xhr.responseJSON).map(([key, value]) => `${key !== 'non_field_errors' ? (key + ': ') : ''}${Array.isArray(value) ? value.join(', ') : value}`).join('; ');
            }
            $('#producePartAlerts').html(`<div class="alert alert-danger">${displayError}</div>`).show();
        },
        true, $button, originalButtonText
    );
}

// =================================================================================
// SPECIFIC DATA VIEWS (Assigned Work Orders, Personnel, Teams)
// =================================================================================

/**
 * Montajcı personele atanmış (veya atanabilecek) iş emirlerini API'den (`work-orders/`) çekerek DataTables ile listeler.
 * Backend, isteği yapan kullanıcıya göre filtreleme yapar. Sunucu tarafı işleme destekler.
 */
function fetchAssignedWorkOrders() {
    const tableElement = $('#assignedWorkOrdersTable');
    $('#assignedWorkOrderAlerts').empty();

    if (typeof $.fn.DataTable !== 'function') {
        console.error("DataTables JS kütüphanesi yüklenmemiş!");
        $('#assignedWorkOrderAlerts').html('<div class="alert alert-danger">Tablo bileşeni yüklenemedi.</div>');
        return;
    }

    if ($.fn.DataTable.isDataTable(tableElement)) {
        assignedWorkOrdersDataTable.ajax.reload();
        return;
    }
    
    console.info("Initializing Assigned WorkOrders DataTable for Assembler...");
    assignedWorkOrdersDataTable = tableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}work-orders/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function (d) {
                const drfParams = {
                    length: d.length === -1 ? 99999 : d.length,
                    start: d.start,
                    draw: d.draw 
                };
                if (d.search && d.search.value) { drfParams.search = d.search.value; }
                if (d.order && d.order.length > 0) {
                    const orderColumnIndex = d.order[0].column;
                    const orderDirection = d.order[0].dir;
                    let orderColumnName = d.columns[orderColumnIndex].data; 
                    const orderingFieldMap = {
                        'aircraft_model_name': 'aircraft_model__name',
                        'status_display': 'status',
                        'assigned_to_assembly_team_name': 'assigned_to_assembly_team__name'
                    };
                    let sortableFieldName = orderingFieldMap[orderColumnName] || orderColumnName;
                    if (sortableFieldName) {
                        drfParams.ordering = (orderDirection === 'desc' ? '-' : '') + sortableFieldName;
                    }
                }

                return drfParams;
            },
            error: function (xhr) {
                hideSpinner();
                let errorMsg = "Atanmış iş emirleri yüklenirken bir hata oluştu.";

                $('#assignedWorkOrderAlerts').html(`<div class="alert alert-danger">${errorMsg}</div>`);
            }
        },
        columns: [
            { data: "id", title: "ID" },
            { data: "aircraft_model_name", title: "Uçak Modeli", defaultContent: "-" },
            { data: "quantity", title: "Miktar" },
            { data: "status_display", title: "Durum", render: function(data, type, row){ 
                let badgeClass = 'bg-light text-dark'; 
                if (row.status === 'PENDING') badgeClass = 'bg-warning text-dark';
                else if (row.status === 'ASSIGNED') badgeClass = 'bg-primary text-white';
                else if (row.status === 'IN_PROGRESS') badgeClass = 'bg-info text-dark';
                return `<span class="badge ${badgeClass}">${data || 'Bilinmiyor'}</span>`;
            }},
            { data: "assigned_to_assembly_team_name", title: "Atanan Takım", defaultContent: "Atanmamış" },
            { data: "created_at", title: "Oluşturma Tarihi", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            { data: "target_completion_date", title: "Hedef Tarih", render: function(data) { return data ? new Date(data).toLocaleDateString('tr-TR') : '-'; }},
            // Montajcı için işlemler sütunu şimdilik boş veya farklı butonlar içerebilir.
            // { data: null, title: "İşlemler", orderable: false, searchable: false, defaultContent: "-" }
        ],
        order: [[0, 'desc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}

/**
 * Ana panel (dashboard) için stok uyarılarını API'den (`inventory/stock-levels/`) çekerek gösterir.
 * Sadece kritik (tükenmiş) stokları listeler. Datatable uyumludur.
 */
function displayDashboardStockWarningsFromStockLevelsAPI() {
    const params = {
        stock_type: 'parts',
        length: -1,
        start: 0
    };

    makeApiRequest('inventory/stock-levels/', 'GET', params, 
        function(response) {
            const stockData = response.data || []; 
            let collectedWarnings = [];

            stockData.forEach(item => {
                if (item.warning_zero_stock) {
                    collectedWarnings.push(
                        `${item.aircraft_model_name} için ${item.part_type_category_display} stoğu tükendi.`
                    );
                }
            });

            let targetListId = null;
            if (currentUser.is_staff || currentUser.is_superuser) {
                targetListId = '#adminStockWarningsList';
            } else if (currentUser.personnel_profile?.team_type === 'ASSEMBLY_TEAM') {
                targetListId = '#assemblerStockWarningsList';
            } else if (currentUser.personnel_profile && ['WING_TEAM', 'FUSELAGE_TEAM', 'TAIL_TEAM', 'AVIONICS_TEAM'].includes(currentUser.personnel_profile.team_type)) {
                targetListId = '#producerStockWarningsList';
            }

            if (targetListId) {
                const $list = $(targetListId);
                $list.empty();
                if (collectedWarnings.length > 0) {
                    collectedWarnings.forEach(warning => {
                        $list.append(`<li class="alert alert-danger">${warning}</li>`);
                    });
                } else {
                    $list.append('<li class="alert alert-success">Kritik seviyede stok bulunmamaktadır. Her şey yolunda!</li>');
                }
            }
        },
        function(errorMsg) {
            console.error("Stok uyarıları alınamadı:", errorMsg);
            $('#generalDashboardMessages').html(`<div class="alert alert-warning">Stok uyarıları yüklenirken bir sorun oluştu.</div>`);
        }, false); // Arka planda sessizce yüklensin, ana spinner'ı tetiklemesin
}

/**
 * Personel listesini API'den (`personnel/`) çekerek DataTables ile listeler.
 * Sadece Admin/Staff kullanıcıları için çalışır. Sunucu tarafı işleme destekler.
 */
function fetchPersonnel() {
    const tableElement = $('#personnelTable');
    $('#personnelAlerts').empty();
    if (typeof $.fn.DataTable !== 'function') { /* Hata yönetimi */ return; }
    if ($.fn.DataTable.isDataTable(tableElement)) { personnelDataTable.ajax.reload(); return; }

    personnelDataTable = tableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}personnel/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function(d) {  return d; },
            error: function(xhr) { $('#personnelAlerts').html(`<div class="alert alert-danger">Personel listesi yüklenemedi.</div>`); }
        },
        columns: [
            { data: "user", title: "Kullanıcı ID" }, // PersonnelSerializer'dan gelen user ID
            { data: "user_username", title: "Kullanıcı Adı", defaultContent: "-" }, // Serializer'da user_username alanı olmalı
            { data: "user_email", title: "E-posta", defaultContent: "-" }, // Serializer'da user_email alanı olmalı
            { data: "team_name", title: "Takımı", defaultContent: "Atanmamış" }, // Serializer'da team_name alanı olmalı
            { data: null, title: "İşlemler", orderable: false, searchable: false, render: function(data,type,row){
                return `<button class="btn btn-sm btn-warning btn-edit-personnel me-1" data-id="${row.user}" title="Takım Ata/Değiştir"><i class="fas fa-edit"></i></button>` + 
                       `<button class="btn btn-sm btn-danger btn-delete-personnel" data-id="${row.user}" title="Personeli Sil (Kullanıcıyı Siler)"><i class="fas fa-trash-alt"></i></button>`; 
            }}
        ],
        order: [[1, 'asc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}

/**
 * Personel düzenleme (takım atama/değiştirme) modalını açar ve doldurur.
 * Yeni personel ekleme işlevselliği kaldırılmıştır.
 * @param {string|number} personnelUserId Düzenlenecek personelin User ID'si.
 */
function openPersonnelModal(personnelUserId = null) { // personnelUserId burada User ID'dir
    // Bu fonksiyon artık sadece mevcut personelin takımını düzenlemek için kullanılacak.
    $('#personnelForm')[0].reset();
    $('#personnelId').val('');
    $('#personnelFormError').text('');
    $('#personnelPassword').val(''); // Şifre alanını temizle
    
    // Takım listesini doldur
    makeApiRequest('teams/', 'GET', { length: -1 }, function(response) { // Tüm takımları çek
        const teams = response.data || response; // Pagination durumuna göre
        const select = $('#personnelTeam');
        select.empty().append('<option value="">Takım Seçiniz...</option>');
        if (Array.isArray(teams)) {
            teams.forEach(team => select.append(`<option value="${team.id}">${team.name}</option>`));
        }
    });

    if (personnelUserId) { // Her zaman bir personnelUserId (User ID) ile çağrılacak
        $('#personnelModalLabel').text('Personel Takımını Düzenle');
        $('#personnelPasswordGroup').hide(); // Mevcut personel için şifre alanı gizlenir (ayrı bir şifre değiştirme özelliği olabilir)
        $('#personnelUsername').prop('readonly', true);
        $('#personnelEmail').prop('readonly', true);

        makeApiRequest(`personnel/${personnelUserId}/`, 'GET', null, function(data) {
            $('#personnelId').val(data.user); // Personnel'in user ID'si
            $('#personnelUsername').val(data.user_username || 'N/A');
            $('#personnelEmail').val(data.user_email || 'N/A');
            $('#personnelTeam').val(data.team || ''); // data.team ID olmalı
        });
    } else {
        // Bu senaryo artık olmayacak, "Yeni Personel Ekle" butonu kaldırıldı.
        // Eğer bir şekilde ID olmadan çağrılırsa hata verilebilir veya modal kapatılabilir.
        console.error("openPersonnelModal, personnelUserId olmadan çağrıldı. Bu beklenen bir durum değil.");
        $('#personnelModal').modal('hide');
        return;
    }
    $('#personnelModal').modal('show');
}

/**
 * Personel bilgilerini (sadece takımını) günceller. API'ye (`personnel/{id}/`) PATCH isteği yapar.
 */
function savePersonnel() {
    const personnelUserId = $('#personnelId').val(); // Bu User ID
    if (!personnelUserId) {
        $('#personnelFormError').text('Kaydedilecek personel bulunamadı.');
        return;
    }

    const formData = {
        team: $('#personnelTeam').val() || null // Sadece takım güncelleniyor
    };
    const method = 'PATCH'; // Her zaman mevcut personelin takımını güncelliyoruz
    const endpoint = `personnel/${personnelUserId}/`;
    
    $('#personnelFormError').text('');

    makeApiRequest(endpoint, method, formData,
        function(response) {
            $('#personnelModal').modal('hide');
            $('#personnelAlerts').html(`<div class="alert alert-success">Personelin takımı başarıyla güncellendi.</div>`);
            if (personnelDataTable) personnelDataTable.ajax.reload(null, false);
        },
        function(errorMsg) { $('#personnelFormError').text(errorMsg); },
        true, $('#savePersonnelBtn')
    );
}

/**
 * Takım listesini API'den (`teams/`) çekerek DataTables ile listeler.
 * Sadece Admin/Staff kullanıcıları için çalışır. Sunucu tarafı işleme destekler.
 */
function fetchTeams() {
    const tableElement = $('#teamsTable');
    $('#teamAlerts').empty();
    if (typeof $.fn.DataTable !== 'function') { /* Hata yönetimi */ return; }
    if ($.fn.DataTable.isDataTable(tableElement)) { teamsDataTable.ajax.reload(); return; }

    teamsDataTable = tableElement.DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: `${API_APP_BASE_URL}teams/`,
            type: "GET",
            headers: { 'Authorization': authToken ? `Token ${authToken}` : '' },
            data: function(d) {  return d; },
            error: function(xhr) { $('#teamAlerts').html(`<div class="alert alert-danger">Takım listesi yüklenemedi.</div>`); }
        },
        columns: [
            { data: "id", title: "ID" },
            { data: "name", title: "Takım Adı" },
            { data: "team_type_display", title: "Takım Tipi" },
            { data: "personnel_count", title: "Personel Sayısı", defaultContent: "0", orderable: false, searchable: false }, // Serializer'da bu alan olmalı
            { data: null, title: "İşlemler", orderable: false, searchable: false, render: function(data,type,row){
                return `<button class="btn btn-sm btn-warning btn-edit-team me-1" data-id="${row.id}" title="Düzenle"><i class="fas fa-edit"></i></button>` +
                       `<button class="btn btn-sm btn-danger btn-delete-team" data-id="${row.id}" title="Sil"><i class="fas fa-trash-alt"></i></button>`;
            }}
        ],
        order: [[1, 'asc']],
        language: { url: DATATABLES_TR_JSON_URL },
        responsive: true, pageLength: 10, lengthMenu: [ [10, 25, 50, -1], [10, 25, 50, "Tümü"] ],
    });
}


/**
 * Yeni takım ekleme veya mevcut takımı düzenleme modalını açar ve doldurur.
 * Takım tiplerini `DefinedTeamTypes` enum'una benzer bir yapıdan (veya API'den) alır.
 * @param {string|number|null} [teamId=null] Düzenlenecek takımın ID'si. Yoksa yeni ekleme modunda açılır.
 */
function openTeamModal(teamId = null) {
    $('#teamForm')[0].reset(); // teamForm ID'li bir form olmalı modalda
    $('#teamId').val(''); // teamId input'u olmalı
    $('#teamFormError').text(''); // teamFormError div'i olmalı

    // Takım tiplerini doldur (DefinedTeamTypes modelinden)
    const teamTypes = {
        "WING_TEAM": "Kanat Takımı",
        "FUSELAGE_TEAM": "Gövde Takımı",
        "TAIL_TEAM": "Kuyruk Takımı",
        "AVIONICS_TEAM": "Aviyonik Takımı",
        "ASSEMBLY_TEAM": "Montaj Takımı"
    };
    const $teamTypeSelect = $('#teamTypeSelect');
    $teamTypeSelect.empty().append('<option value="">Tip Seçiniz:</option>');
    Object.entries(teamTypes).forEach(([key, value]) => $teamTypeSelect.append(`<option value="${key}">${value}</option>`));

    if (teamId) {
        $('#teamModalLabel').text('Takımı Düzenle');
        makeApiRequest(`teams/${teamId}/`, 'GET', null, function(data) {
            $('#teamId').val(data.id);
            $('#teamNameInput').val(data.name);
            $teamTypeSelect.val(data.team_type);
        });
    } else {
        $('#teamModalLabel').text('Yeni Takım Ekle');
    }
    $('#teamModal').modal('show');
}

/**
 * Yeni bir takım oluşturur (POST `teams/`) veya mevcut bir takımı günceller (PUT `teams/{id}/`).
 */
function saveTeam() {
    const teamId = $('#teamId').val();
    const isEditMode = !!teamId;
    const formData = {
        name: $('#teamNameInput').val(),
        team_type: $('#teamTypeSelect').val()
    };
    const method = isEditMode ? 'PUT' : 'POST';
    const endpoint = isEditMode ? `teams/${teamId}/` : 'teams/';

    makeApiRequest(endpoint, method, formData,
        function(response) {
            $('#teamModal').modal('hide');
            $('#teamAlerts').html(`<div class="alert alert-success">Takım başarıyla ${isEditMode ? 'güncellendi' : 'eklendi'}.</div>`);
            if (teamsDataTable) teamsDataTable.ajax.reload(null, false);
        },
        function(errorMsg) { $('#teamFormError').text(errorMsg); }, true, $('#saveTeamBtn'));
}



// =================================================================================
// PAGE INITIALIZATION & EVENT LISTENERS
// =================================================================================

$(document).ready(function() {
    // Gerekli global değişkenlerin tanımlı olup olmadığını kontrol et
    if (typeof LOGIN_PAGE_URL === 'undefined' || typeof DASHBOARD_URL === 'undefined' || 
        typeof API_LOGIN_URL === 'undefined' || typeof API_USER_ME_URL === 'undefined' || 
        typeof API_APP_BASE_URL === 'undefined' || typeof DATATABLES_TR_JSON_URL === 'undefined') {
        console.error("Global URL değişkenlerinden biri veya birkaçı tanımlanmamış!");
        alert("Uygulama başlatılırken kritik bir hata oluştu. Lütfen konsolu kontrol edin.");
        return;
    }

    const currentPath = window.location.pathname;
    const nextUrl = new URLSearchParams(window.location.search).get('next');

    // Giriş sayfasındaysak
    if (currentPath.endsWith(LOGIN_PAGE_URL)) {
        $('#loginForm').off('submit').on('submit', handleLoginSubmit);
        if (authToken && currentUser) { window.location.href = nextUrl || DASHBOARD_URL; }
    } 
    // Dashboard veya alt sayfalarındaysak
    else if (currentPath.startsWith(DASHBOARD_URL.substring(0, DASHBOARD_URL.lastIndexOf('/') + 1))) {
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
    } 
    // Diğer sayfalar (genellikle public olmayan ve giriş gerektiren)
    else { 
        if (authToken && !currentUser) { fetchCurrentUserInfoAndRedirect(); }
    }

    // Dashboard'u başlatan ana fonksiyon
    function initializeDashboard() {
        updateUserInfoDisplayAndMenus();
        let initialContent = 'dashboardContent';
        const hash = window.location.hash.substring(1);
        if(hash && $(`#${hash}Content`).length) { initialContent = `${hash}Content`; }
        else {
            // Eğer hash yoksa veya geçersizse, rolüne göre varsayılan bir sayfa aç
            if (currentUser) {
            // Tüm roller için varsayılan olarak ana paneli aç
            initialContent = 'dashboardContent';
        }
        }
        loadContent(initialContent);
        
        $('#logoutButton').off('click').on('click', handleLogout);

        // Sidebar linkleri için event delegation
        $('.sidebar').off('click', '.nav-link.page-link').on('click', '.nav-link.page-link', function(e) { 
            e.preventDefault(); 
            const targetContentId = $(this).data('target'); 
            loadContent(targetContentId); 
        });
        
        // İş Emri Formu ve Butonları
        $('#saveWorkOrderBtn').off('click').on('click', function() {
            const workOrderId = $('#newWorkOrderModal').data('edit-id');
            saveWorkOrder(workOrderId, $(this)); // Tıklanan butonu makeApiRequest'e iletmek için
        });

        $('#workOrderTableBody').off('click', '.btn-delete-wo').on('click', '.btn-delete-wo', function() {
            const workOrderId = $(this).data('id');
            deleteWorkOrder(workOrderId);
        });

        // Uçak Montaj ve Parça Üretim Formları
        $('#assembleAircraftForm').off('submit').on('submit', handleAssembleAircraftFormSubmit);
        $('#producePartForm').off('submit').on('submit', handleProducePartFormSubmit);

        // İş emri düzenleme butonu (event delegation ile)
        $('#workOrderTableBody').off('click', '.btn-edit-wo').on('click', '.btn-edit-wo', function() {
            const workOrderId = $(this).data('id');
            $('#newWorkOrderModalLabel').text(`İş Emrini Düzenle #${workOrderId}`);
            $('#newWorkOrderModal').data('edit-id', workOrderId);
            makeApiRequest(`work-orders/${workOrderId}/`, 'GET', null, 
                function(data) { populateWorkOrderFormDropdowns(data); },
                function(errorMsg) { $('#workOrderAlerts').html(`<div class="alert alert-danger">Düzenlenecek iş emri verileri alınamadı: ${errorMsg}</div>`); }
            );
        });
        // İş emri modalı kapandığında formu sıfırla
        $('#newWorkOrderModal').on('hidden.bs.modal', function () {
            $('#newWorkOrderForm')[0].reset();
            $('#newWorkOrderModal').removeData('edit-id');
            $('#newWorkOrderModalLabel').text('Yeni İş Emri Oluştur');
            $('#woAircraftModelContainer').empty().removeClass('row g-2 aircraft-model-selector-grid'); // Model seçiciyi temizle
            $('#newWorkOrderError').text('');
        });
        //İş Emri Durum Filtresi Event Listener
        if ($('#workOrderStatusFilter').length) { // Eğer filtre dropdown'ı varsa
            $('#workOrderStatusFilter').on('change', function() {
                if (workOrdersDataTable) {
                    workOrdersDataTable.ajax.reload(); // DataTable'ı yeni filtreyle yeniden yükle
                }
            });
        }

        // Parça Filtreleri için Event Listener'lar
        $('#adminPartStatusFilter, #adminPartCategoryFilter, #adminPartAircraftModelFilter').on('change', function() {
            if (adminPartsDataTable && $('#partsContent').is(':visible')) {
                adminPartsDataTable.ajax.reload();
            }
        });
        $('#producerPartStatusFilter, #producerPartAircraftModelFilter').on('change', function() {
            if (myTeamPartsDataTable && $('#myTeamPartsContent').is(':visible')) {
                myTeamPartsDataTable.ajax.reload();
            }
        });

        // Uçak Filtreleri için Event Listener'lar
        $('#aircraftStatusFilter, #aircraftModelFilter, #aircraftTeamFilter').on('change', function() {
            if (aircraftsDataTable && $('#aircraftsContent').is(':visible')) {
                aircraftsDataTable.ajax.reload();
            }
        });

        // Personel ve Takım Modal Açma Butonları
        $('#btnOpenNewTeamModal').on('click', function() { 
            openTeamModal(); // Takım modalını açmak için HTML'de teamForm, teamId, teamNameInput, teamTypeSelect, teamFormError elemanları olmalı
        });
        // Personel ve Takım Kaydetme/Silme Butonları
        $('#savePersonnelBtn').on('click', function() { savePersonnel(); });
        $('body').off('click', '.btn-edit-personnel').on('click', '.btn-edit-personnel', function() {
            const personnelUserId = $(this).data('id');
            openPersonnelModal(personnelUserId);
        });
        
        $('body').off('click', '.btn-delete-personnel').on('click', '.btn-delete-personnel', function() {
            const personnelUserId = $(this).data('id');
            if (confirm(`Personel (Kullanıcı ID: ${personnelUserId}) ve ilişkili kullanıcı hesabı silinecek. Bu işlem geri alınamaz. Emin misiniz?`)) {
                makeApiRequest(`personnel/${personnelUserId}/`, 'DELETE', null,
                    function() { if (personnelDataTable) personnelDataTable.ajax.reload(null, false); $('#personnelAlerts').html('<div class="alert alert-info">Personel silindi.</div>'); },
                    function(errorMsg) { $('#personnelAlerts').html(`<div class="alert alert-danger">Personel silinirken hata: ${errorMsg}</div>`); }
                );
            }
        });
        $('#saveTeamBtn').on('click', function() { saveTeam(); });
        $('body').off('click', '.btn-edit-team').on('click', '.btn-edit-team', function() {
            const teamId = $(this).data('id');
            if (teamId) {
                openTeamModal(teamId);
            } else {
                console.error("Düzenlenecek takım ID'si bulunamadı.");
            }
        }); 
        $('body').off('click', '.btn-delete-team').on('click', '.btn-delete-team', function() {
            const teamId = $(this).data('id');
            if (confirm(`Takım #${teamId} silinecek. Bu işlem geri alınamaz. Emin misiniz? (Takımdaki personeller takımsız kalacaktır.)`)) {
                makeApiRequest(`teams/${teamId}/`, 'DELETE', null,
                    function() { if (teamsDataTable) teamsDataTable.ajax.reload(null, false); $('#teamAlerts').html('<div class="alert alert-info alert-dismissible fade show" role="alert">Takım başarıyla silindi.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>'); },
                    function(errorMsg) { $('#teamAlerts').html(`<div class="alert alert-danger alert-dismissible fade show" role="alert">Takım silinirken hata: ${errorMsg}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`); }
                );
            }
        }); 
        
        // Geri Dönüştürme Butonu için Event Delegation
        $('body').on('click', '.btn-recycle-part', function() {
            const partId = $(this).data('id');
            if (confirm(`Parça #${partId} geri dönüştürülecek (silinecek). Emin misiniz?`)) {
                makeApiRequest(`parts/${partId}/`, 'DELETE', null,
                    function() {
                        // İlgili DataTable'ı yeniden yükle
                        if (adminPartsDataTable && $('#partsContent').is(':visible')) adminPartsDataTable.ajax.reload(null, false);
                        else if (myTeamPartsDataTable && $('#myTeamPartsContent').is(':visible')) myTeamPartsDataTable.ajax.reload(null, false);
                        
                        if ($('#partsContent').is(':visible')) {
                            $('#adminPartsAlerts').html('<div class="alert alert-info alert-dismissible fade show" role="alert">Parça geri dönüştürüldü.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>');
                        }
                        if ($('#myTeamPartsContent').is(':visible')) {
                            $('#myTeamPartsAlerts').html('<div class="alert alert-info alert-dismissible fade show" role="alert">Parça geri dönüştürüldü.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>');
                        }
                    },
                    function(errorMsg) {
                        alert(`Parça geri dönüştürülürken hata: ${errorMsg}`);
                    }
                );
            }
        });

        $('body').on('click', '.btn-recycle-aircraft', function() {
            const aircraftId = $(this).data('id');
            if (confirm(`Uçak #${aircraftId} geri dönüştürülecek (silinecek). Emin misiniz?`)) {
                makeApiRequest(`aircraft/${aircraftId}/`, 'DELETE', null,
                    function() {
                        if (aircraftsDataTable && $('#aircraftsContent').is(':visible')) aircraftsDataTable.ajax.reload(null, false);
                        $('#aircraftsAlerts').html('<div class="alert alert-info alert-dismissible fade show" role="alert">Uçak geri dönüştürüldü.<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>');
                    },
                    function(errorMsg) {
                        alert(`Uçak geri dönüştürülürken hata: ${errorMsg}`);
                    }
                );
            }
        });

    }
});
