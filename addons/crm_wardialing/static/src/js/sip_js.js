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
		console.log("CALL FUNCTION")
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
			$('.oe_dial_big_callbutton').html("Calling...");
			$(".oe_dial_inCallButton").removeAttr('disabled');
			//Make the call
			this.session = this.ua.invite(number,this.call_options);
			//Bind action when the call is answered
			this.session.on('accepted',function(){
				console.log("ACCEPTED");
				self.onCall = true;
				new openerp.web.Model("crm.phonecall").call("init_call", [self.phonecall.id]);
			});

			this.session.on('rejected',function(){
				console.log("REJECTED");
				self.session = false;
				var phonecall_model = new openerp.web.Model("crm.phonecall");
				phonecall_model.call("rejected_call",[self.phonecall.id]);
				$('.oe_dial_big_callbutton').html("Call");
				$(".oe_dial_inCallButton").attr('disabled','disabled');
			});

			this.session.on('cancel',function(){
				console.log("CANCEL");
				self.session = false;
				console.log("cancel - disable button");
				$('.oe_dial_big_callbutton').html("Call");
				$(".oe_dial_inCallButton").attr('disabled','disabled');
			});
			this.session.on('bye',function(){
				console.log("BYE");
				var phonecall_model = new openerp.web.Model("crm.phonecall");
				phonecall_model.call("hangup_call", [self.phonecall.id]).then(function(result){
					openerp.web.bus.trigger('reload_panel');
					self.session = false;
					self.onCall = false;
					console.log(result.duration)
					self.phonecall.duration = parseFloat(result.duration).toFixed(2);
					console.log("Hangup");
					console.log(self.phonecall.duration);
					$('.oe_dial_big_callbutton').html("Call");
					$(".oe_dial_inCallButton").attr('disabled','disabled');
					self.loggedCallOption();
				});	
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
			this.session.refer(this.config.physicalPhone);
		}
	}

	this.loggedCallOption = function(){
		var value = this.phonecall.duration;
		var pattern = '%02d:%02d';
        if (value < 0) {
            value = Math.abs(value);
            pattern = '-' + pattern;
        }
        var hour = Math.floor(value);
        var min = Math.round((value % 1) * 60);
        if (min == 60){
            min = 0;
            hour = hour + 1;
        }
		if(this.phonecall.description == ""){
			this.phonecall.description = "Call " + _.str.sprintf(pattern, hour, min) + " min(s) about " + this.phonecall.name;
		}
		console.log(this.phonecall);
		openerp.client.action_manager.do_action({
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': this.phonecall.id,
                'opportunity_id': this.phonecall.opportunity_id,
                'default_name': this.phonecall.name,
                'default_duration': this.phonecall.duration,
                'default_description' : this.phonecall.description,
                'default_opportunity_name' : this.phonecall.opportunity_name,
                'default_opportunity_planned_revenue' : this.phonecall.opportunity_planned_revenue,
                'default_opportunity_title_action' : this.phonecall.opportunity_title_action,
                'default_opportunity_date_action' : this.phonecall.opportunity_date_action,
                'default_opportunity_probability' : this.phonecall.opportunity_probability,
                'default_partner_name' : this.phonecall.partner_name,
                'default_partner_phone' : this.phonecall.partner_phone,
                'default_partner_email' : this.phonecall.partner_email,
                'default_partner_image_small' : this.phonecall.partner_image_small,},
                views: [[false, 'form']],
            });
	}
}