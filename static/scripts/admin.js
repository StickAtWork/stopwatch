$(document).ready(function(){
    var $admin = $('#admin_editor');
    
    /*
        type editor functions
    */
    $admin.on('click', '#type_table tr', function(){
        var $this = $(this);
        var $editor = $('#type_editor');
        
        //set correct values
        $('input[name=description]', $editor).val($('td', $this)[0].innerHTML);
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
    
    /*
        user editor functions
    */
    $admin.on('click', '#user_table tr', function(){
        var $this = $(this);
        var $editor = $('#user_editor');
        
        //set values. popup requires some string matching hacky sack
        var $values = $('td', $this);
        console.log($values);
        $('input[name=name]', $editor).val($values[0].innerHTML);
        $('input[name=email]', $editor).val($values[1].innerHTML);
        //behold the hacky sack
        $('select[name=usergroup] option', $editor).filter(function() {
                return $(this).text() == $values[2].innerHTML;
            }).prop('selected', true);
        $('input[name=user-id]', $editor).attr('value', $this.attr('data-id'));
        
        $this.siblings().removeClass("selected");
        $this.addClass("selected");
    });
    
    /* buttons */
    $admin.on('click', 'button', function(){
        var $this = $(this);
        var $parent = $this.parent();
        var fdata = $parent.serializeArray();
        $.ajax({
            method: 'post',
            url: $this.attr("formaction"),
            data: fdata
        }).success(function(data){
            $parent.parent().empty().append(data);
        });
        return false;
    });
});