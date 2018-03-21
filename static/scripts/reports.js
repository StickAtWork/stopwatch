/**
 * Handlers for the Reports view go here.
 */

$(document).ready(function(){
    $('button[type=submit]').on('click', function(){
        var $this = $(this);
        var fdata = $this.parent().serializeArray();
        $.ajax({
           method: 'post',
           url: $(this).attr('formaction'),
           data: fdata
        }).success(function(data){
            $('#report-results').empty().html(data);
        });
        return false;
    });
});