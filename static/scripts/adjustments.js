$(document).ready(function(){
    var $main = $('#main');
    
    /* initial search for the project_id */
    $('button[type=submit]').on('click', function(){
        var $this = $(this);
        var fdata = $this.parent().serializeArray();
        $.ajax({
           method: 'post',
           url: $(this).attr('formaction'),
           data: fdata
        }).success(function(data){
            $('#adjustment_search_results').html(data);
        });
        return false;
    });
    
    /* sends any changes to a row back to the db to auto-update */
    $('#adjustment_search_results', $main).on('change', 
                                              'input, select', 
                                              function() {
        var $this_row = $(this).parents('tr');
        //can't just use serializeArray() because of how the elements
        //are nested. so this is a lot of code but it works right.
        //...mumble mumble should have used React mumble
        var fdata = {
            "project-id": $this_row.parents('table').attr('data-project-id'),
            "record-id": $this_row.attr('data-record-id'),
            "start": $('input[name=start]', $this_row).val(),
            "stop": $('input[name=stop]', $this_row).val(),
            "phase": $('select[name=phase]', $this_row).val()
        };
        $.ajax({
            url: "/adjustments/edit_time_records",
            method: "post",
            data: fdata
        }).success(function(data){
            $('#adjustment_search_results').html(data);
        })
    });
});