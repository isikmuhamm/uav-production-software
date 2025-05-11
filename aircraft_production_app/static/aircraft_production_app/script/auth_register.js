/**
 * Yeni kullanıcı kaydı işlemleri için event handler ve AJAX fonksiyonları.
 */
$(document).ready(function() {
    /**
     * Kayıt formunun submit olayını dinler ve AJAX ile API'ye gönderir.
     * @param {Event} event - Form gönderim olayı
     */
    $('#registerForm').on('submit', function(event) {
        event.preventDefault();

        const $form = $(this);
        const $button = $('#registerButton');
        const originalText = $button.html();
        const $alerts = $('#registerAlerts');

        $alerts.empty().removeClass('alert alert-danger alert-success');
        $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Kayıt Olunuyor...');

        const formData = {
            username: $('#regUsername').val(),
            email: $('#regEmail').val(),
            password: $('#regPassword').val(),
            password2: $('#regPassword2').val()
        };

        /**
         * @description API_REGISTER_URL ile POST isteği atarak kullanıcı kaydı oluşturur.
         * API'den başarılı yanıt alındığında kullanıcıya bilgi mesajı gösterir.
         */
        $.ajax({
            url: typeof API_REGISTER_URL !== 'undefined' ? API_REGISTER_URL : '/register/',
            method: 'POST',
            data: JSON.stringify(formData),
            contentType: 'application/json; charset=utf-8',
            success: function(response) {
                $button.prop('disabled', false).html(originalText);
                $alerts.html(response.message || 'Kayıt başarılı!').addClass('alert alert-success').show();
                $form[0].reset();
                setTimeout(function() {
                    if (typeof LOGIN_URL !== 'undefined') {
                        window.location.href = LOGIN_URL;
                    }
                }, 3000);
            },
            error: function(xhr) {
                $button.prop('disabled', false).html(originalText);
                let errorMsg = 'Kayıt sırasında bir hata oluştu.';
                if (xhr.responseJSON) {
                    errorMsg = Object.entries(xhr.responseJSON).map(([field, value]) => {
                        let translatedField = field;
                        if (field === 'username') translatedField = 'Kullanıcı Adı';
                        else if (field === 'email') translatedField = 'E-posta';
                        else if (field === 'password') translatedField = 'Şifre';
                        else if (field === 'password2') translatedField = 'Şifre Tekrar';
                        else if (field === 'non_field_errors') return value;
                        return `${translatedField}: ${Array.isArray(value) ? value.join(', ') : value}`;
                    }).join('<br>');
                }
                $alerts.html(errorMsg).addClass('alert alert-danger').show();
            }
        });
    });
});