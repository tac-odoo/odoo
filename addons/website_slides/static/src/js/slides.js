jQuery(document).ready(function() {
    var website = openerp.website;

	$("timeago.timeago").timeago();
    $('.slide-container').click(function(ev){
        window.location = $(this).find("a").attr("href");
    });
    $('.slide-tabs').click(function(ev){
        ev.preventDefault();
        window.location = $(this).attr('href');
    });

    $('.slide-like, .slide-unlike').on('click' ,function(ev){
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc($link.data('href'), 'call', {}).then(function(data){
                $($link.data('count-el')).text(data);
        });
    });
    $('.upload').on('click' ,function(ev){
        new website.slide.Dialog(this).appendTo(document.body);
    });
    /*modify embed code based on options*/
    jQuery.modifyembedcode = function(currentVal) {
        var slide_embed_code = jQuery('#slide_embed_code').val();
        var new_slide_embed_code = slide_embed_code.replace(/(page=).*?([^\d]+)/,'$1' + currentVal + '$2');
        jQuery('#slide_embed_code').val(new_slide_embed_code);
    };
	// This button will increment the value
    jQuery('#btnplus').click(function(e){
        e.preventDefault();
        fieldName = jQuery(this).attr('field');
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());
        if (!isNaN(currentVal)) {
            if(currentVal < jQuery('#pdf_page_count').val()){
                jQuery('input[name='+fieldName+']').val(currentVal + 1);
                jQuery.modifyembedcode(currentVal + 1)
            }else{
                jQuery('input[name='+fieldName+']').val(currentVal);
                jQuery.modifyembedcode(currentVal)
            }
        } else {
            jQuery('input[name='+fieldName+']').val(1);
            jQuery.modifyembedcode(1)
        }
    });
    // This button will decrement the value till 0
    jQuery("#btnminus").click(function(e) {
        e.preventDefault();
        fieldName = jQuery(this).attr('field');
        var currentVal = parseInt(jQuery('input[name='+fieldName+']').val());
        if (!isNaN(currentVal) && currentVal > 1) {
            jQuery('input[name='+fieldName+']').val(currentVal - 1);
            jQuery.modifyembedcode(currentVal - 1)
        } else {
            jQuery('input[name='+fieldName+']').val(1);
            jQuery.modifyembedcode(1)
        }
    });

});
