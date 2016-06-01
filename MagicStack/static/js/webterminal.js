
/**
 * Created by liuzheng on 3/3/16.
 */

var rowHeight = 1;
var colWidth = 1;
var unique_id = '';
var log_id = '';
var term_client = ''
function WSSHClient() {
}
WSSHClient.prototype._generateEndpoint = function (options) {
    console.log(options);
    var protocol = '';
    if (window.location.protocol == 'https:') {
        protocol = 'wss://';
    } else {
        protocol = 'ws://';
    }

    var url_params = document.URL.match(/(\?.*)/)[0].split('&')[3];
    var proxy_url = url_params.split('=')[1]+'/';
    var server_ip = proxy_url.match(RegExp('//(.*?)/'))[1];
    var endpoint = protocol + server_ip + '/v1.0/ws/terminal' + document.URL.match(/(\?.*)/)[0];
    var unique_id_param = document.URL.match(/(\?.*)/)[0].split('&')[0];
    unique_id = unique_id_param.split('=')[1];
    return endpoint;
};
WSSHClient.prototype.connect = function (options) {
    var endpoint = this._generateEndpoint(options);

    if (window.WebSocket) {
        this._connection = new WebSocket(endpoint);
    }
    else if (window.MozWebSocket) {
        this._connection = MozWebSocket(endpoint);
    }
    else {
        options.onError('WebSocket Not Supported');
        return;
    }

    this._connection.onopen = function () {
        options.onConnect();
    };

    this._connection.onmessage = function (evt) {
        try{
            options.onData(evt.data);
        } catch (e) {
            var data = JSON.parse(evt.data.toString());
            options.onError(data.error);
        }
    };

    this._connection.onclose = function (evt) {
        options.onClose();

    };
};

WSSHClient.prototype.send = function (data) {
    this._connection.send(JSON.stringify({'data': data}));
};

function openTerminal(options) {
    var client = new WSSHClient();
    var term = new Terminal({
        rows: rowHeight,
        cols: colWidth,
        useStyle: true,
        screenKeys: true
    });
    term.open();
    term.on('data', function (data) {
        client.send(data)
    });
    $('.terminal').detach().appendTo('#term');
    term.resize(80, 24);
    term.write('Connecting...');
    client.connect($.extend(options, {
        onError: function (error) {
            term.write('Error: ' + error + '\r\n');
        },
        onConnect: function () {
            // Erase our connecting message
            term.write('\r');
        },
        onClose: function () {
            term.write('Connection Reset By Peer');
            var param = {'asset_id': unique_id, 'log_id': log_id};
            $.post('/log/record/save/', param, function(resp){
                    if(resp.success == 'false'){
                          alert(resp.error)
                      }
            }, 'json');
        },
        onData: function (data) {
            if(data.indexOf('Last login') >0 ){
                var pindex = data.indexOf(']');
                var log_content = data.slice(1, pindex);
                log_id = log_content.split('=')[1];
                data = data.slice(pindex+1);
                var url = '/log/record/save/?asset_id=' + unique_id + '&log_id=' + log_id;
                $.get( url , function (resp) {
                      if(resp.success == 'false'){
                          alert(resp.error)
                      }
                }, 'json')
            }
            term.write(data);
        }
    }));
    rowHeight = 0.0 + 1.00 * $('.terminal').height() / 24;
    colWidth = 0.0 + 1.00 * $('.terminal').width() / 80;
    return {'term': term, 'client': client};
}

function resize() {
    $('.terminal').css('width', window.innerWidth - 25);
    console.log(window.innerWidth);
    console.log(window.innerWidth - 10);
    var rows = Math.floor(window.innerHeight / rowHeight) - 2;
    var cols = Math.floor(window.innerWidth / colWidth) - 1;
    return {rows: rows, cols: cols};
}


$(document).ready(function () {
    var options = {};
    $('#ssh').show();
    term_client = openTerminal(options);
    console.log(rowHeight);

});

