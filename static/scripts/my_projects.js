$(document).ready(function(){    
    /*  loads ticket into expanded view
    
    */
    var $proj_view = $('#project-view');
    
    $proj_view.on('click', "#projects tr", function(){
        var $this = $(this);
        var project_id = $this.attr('data-row');
        if (project_id === undefined) {
            return false;
        }
        $.ajax({
            url: "expanded_project",
            method: "POST",
            data: project_id
        }).success(function(data){
            $('#expanded-project').empty().append(data);
            $this.siblings().removeClass("selected");
            $this.addClass("selected");
        });
    });
    
    $proj_view.on('click', 'button', function(){
        $.ajax({
            url: $(this).attr('formaction'),
            method: "POST"
        }).success(function(data){
            $proj_view.empty().append(data);
        });
    });
    
    /*  timer handler
    
    */
    
    $('#main form#timer').on('submit', function(){
        var fdata = $(this).serializeArray();
        var do_submit = fdata[0]["value"] !== undefined;
        if(!do_submit) {
            alert("Please select a timeable item.");
        } else {
            if(fdata[0]["value"] == 'Horse') {
                alert("Got 'Horse' instead of 'int', assumed test");
            }
        }
        return false;
    });
    
    
    
    /*  handlers for expanded project view
    
        just try not to dynamically load #expanded-project, kthx        
    
    */
    var $exp_proj = $("#expanded-project");
    
    $exp_proj.on('click', "button.shutter", function(){
        var $this = $(this);
        $this.siblings().toggle();
        $this.toggleClass('closed');
    });
    
    $exp_proj.on('click', '#action_items div.content tr', function(){
        var $this = $(this);
        var data_id = $this.attr('data-id');
        if (data_id === undefined) {
            return false;
        }
        $this.siblings().removeClass("selected");
        $this.addClass("selected");
        //update the action item controller thing with
        //these values
        
        var $ai_editor = $('#new_action_item');
        
        //a bunch of string matching to set the values on the
        //action item editor. maybe doesn't need to be a loop, it's
        //probably prudent to refactor this. i'm just being lazy yo
        $ai_editor.children().each(function(index, el){
            var $el = $(el);
            var $value = $('td', $this).eq(index).text();
            //name
            if (index == 0) {
                $el.val($value);
            }
            //type
            if (index == 1) {
                //when this returns true, it's found a match.
                //sets the dropdown to the matched item
                $('option', $el).filter(function() {
                    return $(this).text() == $value;
                }).prop('selected', true);
            }
            //rate
            if (index == 2) {
                $('option', $el).filter(function() {
                    //need the fee per hr from the adjacent
                    //column to correctly match the string
                    return $(this).text() == $value + " @ " + $('td', $this)
                                                                .eq(index + 1)
                                                                .text();
                    
                }).prop('selected', true);
            }
            //data-id
            if (index == 3) {
                $el.attr('value', $this.attr('data-id'));
            }
        });
    });
    
    $exp_proj.on('click', "#new_action_item input[value=Save]", function(event) {
        var $this = $(this);
        var fdata = $this.parent().serializeArray();
        //console.log(fdata);
        $.ajax({
            url: $this.attr("formaction"),
            method: "POST",
            data: fdata
        }).success(function(data){
            $("#action_items .content").html(data);
        });
        return false;
    });
    
    //set default values for a new action item. most importantly setting the 
    //data-id to -1 to signal the server that it's a new item.
    $exp_proj.on('click', "#new_action_item input[value=New]", function(event) {
        $(this).siblings().each(function(index, el){
            //name, type, rate
            if (index < 3) {
                $(el).val('');
            }
            //data-id
            if (index == 3) {
                $(el).attr('value', '-1');
            }
            //we're done here
            if (index > 3) {
                return false;
            }
        });
        return false;
    });
    
    $exp_proj.on('click', '.item-buttons form input', function(){
        var $this = $(this);
        if ($this.attr('value') === 'Delete') {
            if (confirm("Delete this item?") === false) {
                return false;
            }
        }
        var fdata = $this.parent().serializeArray();
        $.ajax({
            url: $this.attr("formaction"),
            method: "POST",
            data: fdata
        }).success(function(data){
            $("#action_items .content").html(data);
        });        
        return false;
    });
    
    
    /*  details handlers
    
    */
    $exp_proj.on('change', '#details form', function(){
        var fdata = $(this).serializeArray();
        $.each(fdata, function(e, i){
            if (i['name'] == "status" && i['value'] == 1) {
                //a Closed ticket will have a value of 1
                //and we will confirm that they actually
                //want to close it
                if (confirm("Close this ticket?" + 
                            "\n\n" + 
                            "It will disappear from " + 
                            "your projects list.") === true) {
                    i['value'] = 2;
                }
            }
        });
        $.ajax({
            url: "/update_details",
            method: "POST",
            data: fdata
        }).success(function(data){
            //should be getting the updated project view back,
            //so that needs to update fer sure
            $proj_view.empty().append(data);
        });
    });
    
    
    /*  phase editor handlers 
    
    */
    $exp_proj.on('click', '#phase-buttons button', function(){
        $.ajax({
            url: $(this).attr("formaction"),
            method: "POST"
        }).success(function(data){
            $("#phases .content").html(data);
        });
        return false;
    });
    
    $exp_proj.on('click', '.phase-view button', function(){
        var $this = $(this);
        $.ajax({
            url: $this.attr("formaction"),
            method: "POST",
            data: $this.attr('value')
        }).success(function(data){
            //send the data to the popup window
            $('#popup-window').trigger('appear', [data]);
        });
        return false;
    });
});