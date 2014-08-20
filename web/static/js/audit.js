var loc = 'ws://' + document.location.host + '/echo';
var connection = new ReconnectingWebSocket(loc);
connection.onopen = function(event) {
    console.log('WebSocket connection created');
};
connection.onmessage = function(event) {
    console.log(event.data)
};
connection.onclose = function(event) {
    console.log("Connection closed");
};
