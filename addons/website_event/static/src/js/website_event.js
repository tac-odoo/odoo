$(document).ready(function () {

    // Catch registration form event, because of JS for attendee details
    $('#registration_form .a-submit')
        .off('click')
        .removeClass('a-submit')
        .click(function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var $form = $(ev.currentTarget).closest('form');
            var post = {};
            $("select").each(function() {
                post[$(this)[0].name] = $(this).val();
            });
            openerp.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $($.parseHTML(modal));
                $modal.appendTo($form).modal()
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                });
            });
        });
});
