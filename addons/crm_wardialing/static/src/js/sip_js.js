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
		if(!this.session){
			var self = this;
			var number;
			this.phonecall = phonecall;
			if(phonecall.partner_phone){
				number = phonecall.partner_phone;
			} else if (phonecall.partner_mobile){
				number = phonecall.partner_mobile;
			}else{
				//TODO what to do when no number? 
				console.log("NO NUMBER");
				return {};
			}
			$('.oe_dial_callbutton').html("Calling...");
			$(".oe_dial_inCallButton").removeAttr('disabled');
			//Make the call
			this.session = this.ua.invite(number,this.call_options);
			//Bind action when the call is answered
			this.session.on('accepted',function(){
				console.log("ACCEPTED");
				self.onCall = true;
			});

			this.session.on('rejected',function(){
				console.log("REJECTED");
				self.session = false;
				$(".oe_dial_inCallButton").attr('disabled','disabled');
			});

			this.session.on('cancel',function(){
				console.log("CANCEL");
				self.session = false;
				console.log("cancel - disable button");
				$('.oe_dial_callbutton').html("Call");
				$(".oe_dial_inCallButton").attr('disabled','disabled');
			});
			this.session.on('bye',function(){
				console.log("BYE");
				var phonecall_model = new openerp.web.Model("crm.phonecall");
				phonecall_model.call("hangup_call", [self.phonecall.id]).then(function(phonecall){
					openerp.web.bus.trigger('reload_panel');
				});
				self.session = false;
				self.onCall = false;
				$('.oe_dial_callbutton').html("Call");
				$(".oe_dial_inCallButton").attr('disabled','disabled');
			});
			
		}
	}
	this.hangup = function(){
		if(this.session){
			if(this.onCall){
				this.session.bye();
			}else{
				this.session.cancel();
			}
		}
		return {};
	}

	this.transfer = function(){
		if(this.session){
			console.log(this.session)
			this.transferSession = this.session.refer(this.config.physicalPhone);

			console.log(this.transferSession);
			this.transferSession.on('bye',function(){
				console.log("BYE TRANSFER");
			});
			this.transferSession.on('accepted',function(){
				console.log("ACCEPTED TRANSFER");
			});
		}
	}
}