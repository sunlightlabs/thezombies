(function($, ReconnectingWebSocket, window, document) {
    "use strict";
    var console = window.console || {log: function(msg) {return msg;}};
    var loc = "ws://" + document.location.host + "/com";
    var connection = new ReconnectingWebSocket(loc);
    connection.onopen = function() {
        console.log("WebSocket connection created");
    };
    connection.onmessage = function(event) {
        var data = JSON.parse(event.data);
        console.log(data);
    };
    connection.onclose = function() {
        console.log("Connection closed");
    };

    $(document).ready(function($) {
        $("a.audit.button").on("click", null, function(event) {
            var id = $(this).data('id');
            var message = {
                id: id,
                audits: 'all'
            }
            connection.send(JSON.stringify(message));
        });
    });
}(jQuery, ReconnectingWebSocket, this, this.document));