/*  handlers for the popup window.

*/

$(document).ready(function(){
    
    /*  custom event; populates .content of popup window,
        makes 'unclickable grey background' appear
        make sure to pass actual content to this function
        wrapped in an array. example:
        
        $('#popup-window').trigger('appear', [myPopupContentHere])
    
    */
    $('#popup-window').on('appear', function(e, info){
        $('#popup-window .content').html(info);
        $('#popup-bg').removeClass('hidden');
        return false;
    });
    
    /*  closes popup window, empties the content area
    
    */
    $('#popup-window #popup-close').on('click', function(){
        $('#popup-window .content').empty();
        $('#popup-bg').addClass('hidden');
        return false;
    });
});