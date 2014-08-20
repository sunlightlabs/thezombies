jQuery(document).ready(function($) {
    $(document).foundation();

    var connection = new ReconnectingWebSocket('ws://localhost:5000/echo');
    connection.onopen = function(event) {
        console.log('WebSocket connection created');
        };
    connection.onmessage = function(event) {
        console.log(event.data)
    };
    connection.onclose = function(event) {
        console.log("Connection closed");
    };

});
