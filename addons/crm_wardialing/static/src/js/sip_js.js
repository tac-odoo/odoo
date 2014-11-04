openerp.sip_js = function(instance) {

	this.init = function() {
		var self = this;
        new openerp.web.Model("crm.phonecall").call("get_pbx_config").then(function(result){
        	console.log(result)
            self.config = result;
            if(result.login && result.wsServer && result.pbx_ip && result.password){
            	var ua_config = {
					uri: result.login +'@'+result.pbx_ip,
					wsServers: result.wsServer,
					authorizationUser: result.login,
					password: result.password,
					hackIpInContact: true,
					log: {level: "error"},
				};
            }else{
            	//TODO handle the error
            	return;
            }
            
			self.ua = new SIP.UA(ua_config);

			var audio = document.createElement("audio");
			audio.id = "remote_audio";
			audio.autoplay = "autoplay";
			document.body.appendChild(audio);
			self.call_options = {
				media: {
					constraints: {
						audio: true,
						video: false,
						stream: self.mediaStream
					},
					render: {
						remote: {
							audio: document.getElementById('remote_audio')
						},
					}
				}
			}
			self.ua.on('invite', function (session){
				console.log(session.remoteIdentity.displayName);
				var confirmation = confirm("Incomming call from " + session.remoteIdentity.displayName);
				if(confirmation){
					session.accept(self.call_options);
				}else{
					session.reject();
				}
			});
        });
	}

	this.call = function(phonecall){
		var self = this;
		var number;
		this.phonecall = phonecall;
		if(phonecall.partner_phone){
			number = phonecall.partner_phone;
		} else if (phonecall.partner_mobile){
			number = phonecall.partner_mobile;
		}
		
		//Make the call
		this.session = this.ua.invite(number,this.call_options);
		//Bind action when the call is answered
		//this.session.on('accepted',function(){this.stream = self.session.getLocalStreams()[0];console.log("ACCEPTED");console.log(this.stream);});
	}

	this.hangup = function(){
		this.session.bye();
	}

	this.transfer = function(){
		this.session.refer(this.config.physicalPhone);
	}
}