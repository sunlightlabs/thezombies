'use strict';
var console = window.console || {log: function(msg) {return msg;}};
var namespace = '/com';
var socket = io.connect('http://' + document.domain + ':' + location.port + namespace);
socket.on('connect', function() {
    socket.emit('my event', {data: 'I\'m connected!'});
});
socket.on('message', function(data) {
    console.log(data);
});

jQuery(document).ready(function($) {
    jQuery('a.audit.button').on('click', null, function(event) {
        event.preventDefault();
        var id = $(this).data('id');
        var data = {
            id: id,
            audits: 'all'
        };
        console.log('Send a message');
        socket.emit('message', data);
    });
});