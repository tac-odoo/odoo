openerp.mail_bubble_chart = function(openerp) {
    var target= [];
    var Interval
    var _t = openerp.web._t,
       _lt = openerp.web._lt;
    var ndata ={
            "author_id": "3",
            "id": "888",
            "message_count": "1",
            "message_date": "2014-03-10 11:17:02",
            "model": "account.invoice",
            "model_name": "Invoice",
            "msg_body": "<p>NDATA</p>",
            "name": "Supplier Invoice ",
            "partner_id": "5",
            "res_id": "1",
            "subject": "false"
    };
        
    var QWeb = openerp.web.qweb;
    var mail = openerp.mail;
    var dataMap,parent;
    openerp.bubble_widget = openerp.web.Widget.extend({
        template: 'BubbleChart',
       
        init: function(parent,action) {
            var self = this;
            this.flag = true;
            this._super.apply(this, arguments);
            this.cRadius=0.0;
            this.width = 500;
            this.height = 300;
            this.padding = -75; // separation between same-color nodes
            this.clusterPadding = 1; // separation between different-color nodes
            this.maxRadius = 70;
            this.model_id = false;
            this.action = _.clone(action);
            this.domain = this.action.params.domain || this.action.domain || [];
            this.context = _.extend(this.action.params.context || {}, this.action.context || {});
            this.ds_bubble = new openerp.web.DataSetSearch(this, 'mail.bubble');
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            var searchview_loaded = this.load_searchview(this.defaults);
            if (! this.searchview.has_defaults) {
                this.search_render();
            }
        },
        
        load_searchview: function (defaults) {
            var self = this;
            this.searchview = new openerp.web.SearchView(this, this.ds_bubble, false, defaults || {}, false);
            this.searchview.appendTo(this.$('.oe_view_manager_view_search'))
                .then(function () { self.searchview.on('search_data', self, self.do_searchview_search); });
            if (this.searchview.has_defaults) {
                this.searchview.ready.then(this.searchview.do_search);
            }
            return this.searchview
        },

        do_searchview_search: function (domains, contexts, groupbys) {
            var self = this;
            openerp.web.pyeval.eval_domains_and_contexts({
                domains: domains || [],
                contexts: contexts || [],
                group_by_seq: groupbys || []
            }).then(function (results) {
                return self.search_render(results);
            });
        },
        search_render: function (search) {
            var self = this;
            var domain = this.domain.concat(search && search['domain'] ? search['domain'] : []);
            var context = _.extend(this.context, search && search['context'] ? search['context'] : {});
            this.ds_bubble.call("bubble_read", [[], domain, context
            ])
            .then(function(results,mod_name) {
                self.render_bubble(results);
            });
        },
        render_bubble: function(bubble_data) {
            bubble_data = d3.nest()
                .key(function(d) { return d.model_name; })
                .entries(bubble_data);
               
            bubble_data.forEach(function(d,i){
                bubble_data[i].root = 'true';
                bubble_data[i].model_id = i ;
                bubble_data[i].message_count = '';
                                    
            });
            
            my_nodes = [];
            this.initiate_data(bubble_data);
            nodes2 = this.load_data(bubble_data, this.model_id, my_nodes);
            this.prepare_chart(nodes2,bubble_data);
        },
           
        initiate_data: function(data) {
            this.cluster_size = _.size(data); // number of distinct clusters = m
            this.color = d3.scale.category10()
                .domain(d3.range(self.cluster_size));
            // The largest node for each cluster.
            this.clusters = new Array(this.cluster_size);
        },
        createBubble: function(model_id,data_record) {
       
            var i = Math.floor(Math.random() * this.cluster_size),
            r = this.maxRadius;
            d = {
                id : data_record['id'],
                count : data_record['message_count'],
                model : data_record['model'],
                res_id : data_record['res_id'],
                cluster: model_id,
                radius: r,
                root : data_record['root'],
                model_name : data_record['key'],
                display_name : data_record['name'], 
                display_subject : data_record['subject'],
                author_id : data_record['author_id'],
                msg_body : data_record['msg_body'],
                x: Math.cos(i / this.cluster_size * 2 * Math.PI) * 400 + this.width / 2 + Math.random(),
                y: Math.sin(i / this.cluster_size * 2 * Math.PI) * 400 + this.height / 2 + Math.random()
                 
            };
           
            if (!this.clusters[model_id] || (r > this.clusters[model_id].radius)) this.clusters[model_id] = d;
            return d
        },
        prepare_chart:function(nodes2,bubble_data) {
            var self = this;
                      
            var force = d3.layout.force()
                .nodes(nodes2)
                .size([this.width, this.height])
                .gravity(0.05)
                .charge(100)
                .on("tick", function(e){ tick(e);})
                .start();
          
                    
            var canvas = d3.select(".bubble_area")
                .append("div")
                .attr("class", "bubble_main");                                         
            var node;
            this.node = canvas.selectAll(".bubble_main")
                .data(force.nodes())
                .enter().append("div")
                .style("background",function(d){if(d.root) return; else return d3.rgb(self.color(d.cluster)).brighter(0.3);})
                
                .style("border-color",function(d){if(d.root) return d3.rgb(self.color(d.cluster));else return  d3.rgb(self.color(d.cluster)).darker(0.5);})  
                .style("height",function(d) {if(d.root) return "80px"; else return (d.radius)+"px"; })
                .style("width",function(d) { if(d.root) return "80px"; else return (d.radius)+"px"; })
                .attr("class",function(d){if(d.root)return "bubble_model"; else return "bubble_node";})
                .attr("id",function(d){if(d.root)return ; else return d.id;})
                .html(function(d) {
                    if(d.root)return "<br><div class='bubble_data' title="+d.model_name+">"+d.model_name;
                    else return "<br><div >"+d.display_name+"<br>"+d.count+"</div>";})
                .on("mouseenter", function(d) { if(d.root) return;else self.animateFirstStep(this);})
                .on("mouseleave", function(d) { if(d.root) return;else self.animateSecondStep(this);})
                .on("click", function(d) {if(d.root) return;else self.animateThirdStep(this);})
                .call(force.drag);
                
                                
                function convertHex(hex,opacity){
                    hex = hex.replace('#','');
                    r = parseInt(hex.substring(0,2), 16);
                    g = parseInt(hex.substring(2,4), 16);
                    b = parseInt(hex.substring(4,6), 16);

                    result = 'rgba('+r+','+g+','+b+','+opacity/100+')';
                    return result;
                }
                
           /*   Interval = setInterval(newNode,10000);
              
             function newNode() {
                
                bubble_data.push(ndata);
                   // self.initiate_data(bubble_data);
                    mydata = []   
                    newnode  = self.load_data(bubble_data, this.model_id,mydata);
                    console.log("new model_id : ",this.model_id);
                    console.log("Updated Node : ",newnode);
                    force
                          .nodes(newnode)
                         .size([this.width, this.height])
                         .gravity(0.05)
                         .charge(100)
                         //.on("tick", function(e){ tick(e);})
                         .start();
                    //force.nodes(newnode);
                    nodes2.forEach(function(d,i){
                        if(nodes2[i].model==ndata.model)
                        {
                            x = d.x;
                            y = d.y;
                            //console.log("Inner X & Y : ",x,y); 
                        }
                        
                    });
                console.log("force.nodes are ",force.nodes())
                self.node
                    .data(newnode)
                    .enter().insert("div")
                    .style("background",function(d){if(d.root) return; else return d3.rgb(self.color(d.cluster));})
                    .style("border-color",function(d){return  d3.rgb(self.color(d.cluster)).darker(0.5);})  
                    .style("height",function(d) {if(d.root) return "80px"; else return (d.radius)+"px"; })
                    .style("width",function(d) { if(d.root) return "80px"; else return (d.radius)+"px"; })
                    .attr("class",function(d){if(d.root)return "model"; else return "node";})
                    .attr("id",function(d){if(d.root)return ; else return d.id;})
                    .style("left",(x+80)+"px").style("top",(y+80)+"px")
                    .html(function(d) {
                        if(d.root)return "<br><div class='data' title="+d.model_name+">"+d.model_name+"</div>";
                        else return "<br>"+d.display_name+"<br>"+d.count+"";})
                    .on("mouseenter", function(d) { if(d.root) return;else self.animateFirstStep(this);})
                    .on("mouseleave", function(d) { if(d.root) return;else self.animateSecondStep(this);})
                    .on("click", function(d) {if(d.root) return;else self.animateThirdStep(this);})
                    .on("tick", function(e){ tick(e);})
                    .call(force.drag);
                    //console.log("X & Y : ",x,y);
                    //.call(tick);
                    //self.node.tick(e);
                                   
                console.log("new node",self.node);
        }*/
        
        
        
        $('.bubble_main').dblclick(function(){    
            d3.selectAll('.bubble_node')        
                .on("mouseenter", function(d) { if(d.root) return;else self.animateFirstStep(this);})
                .on("mouseleave", function(d) { if(d.root) return;else self.animateSecondStep(this);})
                .on("click", function(d) {if(d.root) return;else self.animateThirdStep(this);})  
        }); 
                
        var tick = function(e) {                             
             self.node
                  .each(self.cluster(10 * e.alpha * e.alpha))
                  .each(self.collide(.5, nodes2))
                  .style("left", function(d) { return d.x+"px"; })
                  .style("top", function(d) { return d.y+"px"; })             
                                                    
        };
                                    
        this.node.transition()
            .duration(500)
            .delay(function(d, i) { return i * 100; })
            .attrTween("r", function(d) {
                var i = d3.interpolate(0, d.radius);
                return function(t) { return d.radius = i(t); };
             });                    
        },
        
        destroy: function(){
            this._super();
            clearInterval(Interval);
        },
                    
        load_data: function(data, model_id, nodes1) {
            var self = this;  
            _.each(data, function(data_record) {
                this.model_id = _.has(data_record, 'model_id') ? data_record['model_id'] : this.model_id;
                if(_.has(data_record, 'values')) {
                    self.load_data(data_record['values'], this.model_id, nodes1);
            }        
                d = self.createBubble(this.model_id,data_record);
                nodes1.push(d);
                });
            return nodes1;
        },
                
        animateFirstStep: function(current){          
            var self = this;
            d3.select(current)
              .transition()
              .delay(0)
              .duration(200)
              .style("padding-left","4px")
              .style("height","90px")
              .style("width","90px")
              .style("border-radius","50%").style("opacity",1);                
        },
        
        animateSecondStep: function(current){   
            var self = this;         
            d3.select(current)
              .transition()
                .duration(200)
                .style("height",this.maxRadius+"px")
                .style("width",this.maxRadius+"px")
                .style("background-color", function(d) { return d3.rgb(self.color(d.cluster)).brighter(0.3); })
                .style("border-radius","50%")
                .style("border-style","solid")
                .style("border-width","2px")
                .style("border-color",function(d){return  d3.rgb(self.color(d.cluster)).darker(0.5);})   
                .style("opacity",0.45)
                .style("z-index","5")
                .style("padding","0px")
                 d3.select(current)
                .html( function(d) { 
                if(d.root)return "<br><div class=bubble_data title="+d.model_name+">"+d.model_name+"</div>";
                 else return "<br><div class=bubble_data title="+d.display_name+">"+d.display_name+"<br>"+d.count+"</div>";})
        },
              
        animateThirdStep: function(current){
            d3.selectAll('.bubble_node').on("mouseleave",null);
            d3.selectAll('.bubble_node').on("mouseenter",null);
            d3.selectAll('.bubble_node').on("click",null);
            var self = this;
            d3.select(current)
              .transition().ease("out")
                .delay(0)
                .duration(300)
                .style("width","350px")
                .style("height","350px")                
                .style("border-radius","50%")
                .style("opacity",1)
                .style("background-color","#fff")
                .style("border-style","solid")
                .style("border-width","6px")
                .style("border-color",function(d) { return self.color(d.cluster); })
                .style("z-index","10");
            d3.select(current).style("text-align","center")                
              .html(function(d) { 
                if(d.display_subject){
                    return "<div style='padding:10px 30px 10px 30px'><div class='bubble_expanded_nodeheader'><a href=/web#model="+d.model+"&id="+d.res_id+">"+d.display_subject+"</a></div><div class='bubble_expanded_nodedata'>"+d.msg_body+"</div><img style='padding-top:20px;padding-bottom;20px;' style='border:solid 2px;' src =http://localhost:8069/web/binary/image?model=res.partner&field=image_small&id="+d.author_id+"&resize=/><div><a href=/web#model="+d.model+"&id="+d.res_id+">Read More...</a></div><div>"}
                    
                else {return "<div style='padding:10px 30px 10px 30px'><div class='bubble_expanded_nodeheader'><a href=/web#model="+d.model+"&id="+d.res_id+">NO SUBJECT</a></div><div class='bubble_expanded_nodedata'>"+d.msg_body+"</div><img style='padding-top:20px;padding-bottom;20px;' style='border:solid 2px;' src =http://localhost:8069/web/binary/image?model=res.partner&field=image_small&id="+d.author_id+"&resize=/><div><a href=/web#model="+d.model+"&id="+d.res_id+">Read More...</a></div><div>"}});
        
        
        },
       
        cluster: function(alpha) {
            var self = this;
            return function(d) {
                var cluster = self.clusters[d.cluster];
                if (cluster === d) return;
                var x = d.x - cluster.x,
                  y = d.y - cluster.y,
                  l = Math.sqrt(x * x + y * y),
                  r = d.radius + cluster.radius;
                if (l != r) {
                    l = (l - r) / l * alpha;
                    d.x -= x *= l;
                    d.y -= y *= l;
                    cluster.x += x;
                    cluster.y += y;
              }
            };
        },
        // Resolves collisions between d and all other circles.
        collide: function(alpha, nodes2) {
          var self = this;
          var quadtree = d3.geom.quadtree(nodes2);
          return function(d) {
            var r =  this.maxRadius + Math.min(this.padding, this.clusterPadding),
                nx1 = d.x - r,
                nx2 = d.x + r,
                ny1 = d.y - r,
                ny2 = d.y + r;
            quadtree.visit(function(quad, x1, y1, x2, y2) {
              if (quad.point && (quad.point !== d)) {
                var x = d.x - quad.point.x,
                    y = d.y - quad.point.y,
                    l = Math.sqrt(x * x + y * y),
                    r = d.radius + quad.point.radius + (d.cluster === quad.point.cluster ? self.padding : self.clusterPadding);
                if (l < r) {
                  l = (l - r) / l * alpha;
                  d.x -= x *= l;
                  d.y -= y *= l;
                  quad.point.x += x;
                  quad.point.y += y;
                }
              }
              return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1;
            });
          };
        }
    });
    openerp.web.client_actions.add('mail.bubble.chart','openerp.bubble_widget');
};
