require.config({
    baseUrl: 'static/bower_components',
    paths: {
        jquery: 'jquery/dist/jquery.min',
        foundation: 'foundation/js/foundation.min',
        'jquery.cookie': 'jquery.cookie/jquery.cookie',
        ReconnectingWebSocket: 'reconnectingWebsocket/reconnecting-websocket'
    }
});
require(["jquery", "ReconnectingWebSocket", "foundation", "jquery.cookie"], function(jQuery, ReconnectingWebSocket) {
    $(document).foundation();

    var connection = new ReconnectingWebSocket('ws://localhost:8000/echo');
    connection.onmessage = function(event) {
        console.log(event.data)
    };
    connection.onclose = function(event) {
        console.log("Connection closed");
    };
    console.log('WebSocket connection created');
});
