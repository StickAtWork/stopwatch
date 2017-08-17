$(document).ready(function(){
    var $main = $('#main');
    $('button[type=submit]').on('click', function(){
        //alert('oh yeah');
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
    
    $main.on('change', '#adjustment_search_results input, ' + 
                       '#adjustment_search_results select', function(){
        var $this_row = $(this).parents('tr');
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