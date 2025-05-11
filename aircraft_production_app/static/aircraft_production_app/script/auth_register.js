$(document).ready(function() {
    $('#registerForm').on('submit', function(event) {
        event.preventDefault();
        const $form = $(this);
        const $button = $('#registerButton');
        const originalButtonText = $button.html();
        const $alerts = $('#registerAlerts');

        $alerts.empty().removeClass('alert alert-danger alert-success');
        $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Kayıt Olunuyor...');

        const formData = {
            username: $('#regUsername').val(),
            email: $('#regEmail').val(),
            password: $('#regPassword').val(),
            password2: $('#regPassword2').val()
        };

        // CSRF token'ı header'a eklemek için getCookie fonksiyonuna ihtiyacımız var.
        // Bu fonksiyon main.js'de tanımlı. Eğer bu dosya main.js'den sonra yükleniyorsa erişilebilir.
        // Ya da burada tekrar tanımlanabilir veya base.html'de global bir değişkene atanabilir.
        // Şimdilik makeApiRequest benzeri bir yapı kullanmayıp doğrudan $.ajax kullanıyoruz.
        // CSRF token'ı formdan da alabiliriz: const csrfToken = $form.find('input[name="csrfmiddlewaretoken"]').val();

        $.ajax({
            url: API_REGISTER_URL, // Bu değişken register.html'de tanımlanmalı
            method: 'POST',
            data: JSON.stringify(formData),
            contentType: 'application/json; charset=utf-8',
            // headers: { 'X-CSRFToken': getCookie('csrftoken') }, // Eğer CSRF koruması API'de aktifse
            success: function(response) {
                $button.prop('disabled', false).html(originalButtonText);
                $alerts.html(response.message || 'Kayıt başarılı! Lütfen giriş yapın.').addClass('alert alert-success').show();
                $form[0].reset();
                // İsteğe bağlı: Kullanıcıyı birkaç saniye sonra giriş sayfasına yönlendir
                setTimeout(function() {
                    if (typeof LOGIN_URL !== 'undefined') { // LOGIN_URL register.html'de tanımlanmalı
                        window.location.href = LOGIN_URL;
                    }
                }, 3000);
            },
            error: function(xhr) {
                $button.prop('disabled', false).html(originalButtonText);
                let errorMessage = 'Kayıt sırasında bir hata oluştu.';
                if (xhr.responseJSON) {
                    errorMessage = Object.entries(xhr.responseJSON).map(([key, value]) => {
                        let fieldError = Array.isArray(value) ? value.join(', ') : value;
                        // Alan adlarını daha kullanıcı dostu hale getirebiliriz
                        let fieldName = key;
                        if (key === 'username') fieldName = 'Kullanıcı Adı';
                        else if (key === 'email') fieldName = 'E-posta';
                        else if (key === 'password') fieldName = 'Şifre';
                        else if (key === 'password2') fieldName = 'Şifre Tekrar';
                        else if (key === 'non_field_errors') return fieldError;
                        return `${fieldName}: ${fieldError}`;
                    }).join('<br>');
                }
                $alerts.html(errorMessage).addClass('alert alert-danger').show();
            }
        });
    });
});