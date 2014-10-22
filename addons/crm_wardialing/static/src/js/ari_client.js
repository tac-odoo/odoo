openerp.ari_client = function(instance) {

	this.init = function() {
		console.log("Ari.init");
		if(window.WebSocket) {
			var socket = new WebSocket("ws://localhost:8088");
			
		} else {
	    	alert('Votre navigateur ne supporte pas les webSocket!');
		}
	}
	

	console.log("Ari.client");

};