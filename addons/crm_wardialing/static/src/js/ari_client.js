openerp.ari_client = function(instance) {

	this.init = function() {
		var self = this;
		console.log("Ari.init");
		if(window.WebSocket) {
			console.log("createWebSocket");

			var socket = new WebSocket("ws://localhost:8088/ari/events?api_key=asterisk:asterisk&app=bridge-dial");
			socket.onopen = function() { console.log('socket ouverte'); }
			socket.onmessage = function(message) {
				data = JSON.parse(message.data);
				console.log("MESSAGE RECU: ")
				console.log(data);
				if(data.type=="StasisStart"){
					console.log("STATIS START");
					console.log(data.channel);
					console.log(data.args);
					self.answer(data.channel)
				}
			}
			
		} else {
	    	alert('Votre navigateur ne supporte pas les webSocket!');
		}
	}
	
	this.answer = function(channel){
		$.ajax({
			type: "POST",
			url: "http://localhost:8088/ari/channels/" + channel.id + "/answer",
			username: "asterisk",
			password: "asterisk"
		})
	}

	this.execute = function(param){
		console.log("EXECUTE ");

	}
	console.log("Ari.client");

};