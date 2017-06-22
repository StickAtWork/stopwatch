$(document).ready(function(){
    var $admin = $('#admin_editor');
    
    /*
        type editor functions
    */
    $admin.on('click', '#type_table tr', function(){
        var $this = $(this);
        var $editor = $('#type_editor');
        
        //set correct values
        $('input[name=description]', $editor).val($('td', $this).text());
        $('input[name=type-id]', $editor).attr('value', $this.attr('data-id'));
        
        //highlight the selected thing
        $this.siblings().removeClass("selected");
        $this.addClass("selected");
    });
    
    /*
        rate editor functions
    */
    $admin.on('click', '#rate_table tr', function(){
        var $this = $(this);
        var $editor = $('#rate_editor');
        
        //set both fields equal to the right values
        var $values = $('td', $this);
        $('input[name=description]', $editor).val($values[0].innerHTML);
        $('input[name=fee_per_hour]', $editor).val($values[1].innerHTML);
        $('input[name=rate-id]', $editor).attr('value', $this.attr('data-id'));
        
        //highlight selected thing
        $this.siblings().removeClass("selected");
        $this.addClass("selected");
    });
    
    /* save button */
    $admin.on('click', 'input[type=Submit]', function(){
        var $this = $(this);
        var fdata = $this.parent().serializeArray();
        $.ajax({
            method: 'post',
            url: $this.attr("formaction"),
            data: fdata
        }).success(function(data){
            $this.parent().parent().empty().append(data);
        });
        return false;
    });
});