# -*- coding: utf-8 -*-
import openerp.tests
from openerp.exceptions import AccessError

class TestForum(openerp.tests.HttpCase):
    def test_forum(self):
        cr, uid = self.cr, self.uid
        # Usefull models
        forum_post = self.env['forum.post'];
        forum_post_obj = self.registry['forum.post'];
        forum_tag = self.env['forum.tag'];
        forum_forum = self.env['forum.forum'];
        res_users = self.env['res.users'];
        forum_post_reason = self.env['forum.post.reason'];
        
        # Group's
        group_public_id = self.registry['ir.model.data'].xmlid_to_res_id(cr, uid, 'base.group_public')
        group_portal_id = self.registry['ir.model.data'].xmlid_to_res_id(cr, uid, 'base.group_portal')

        forum_id =  forum_forum.create({
            'name': 'Forum',
        })

        post_reason_id =  forum_post_reason.create({
            'name': 'Not relevant or out dated',
        })

        usera_id =  res_users.create({
            'name': 'Usera',
            'login': 'usera',
            'email': 'usera@gmail.com',
        })
        
        userb_id =  res_users.create({
            'name': 'Userb',
            'login': 'Userb',
            'email': 'userb@gmail.com', 
        })
        
        # public user
        user_public_id = res_users.create({
            'name': 'public user',
            'login': 'public user',
            'email': 'public@example.com',
            'groups_id': [(6, 0, [group_public_id])]
        })

        # portal user
        user_portal_id = res_users.create({
            'name': 'portal user',
            'login': 'portal user',
            'email': 'portal@example.com',
            'groups_id': [(6, 0, [group_portal_id])]
        })

        forum_record = forum_forum.browse(forum_id.id)
        usera_record = res_users.browse(usera_id.id)
        userb_record = res_users.browse(userb_id.id)
        
        # Post with public user
        with self.assertRaises(AccessError):
            forum_post.sudo(user_public_id.id).create({
                'name': " Question ?",
                'forum_id': forum_id.id,
            })
            
        # Post with portal user
        self.assertTrue(forum_post.sudo(user_portal_id.id).create({
                'name': " Question ?",
                'forum_id': forum_id.id,
            }))
        
        # Create 'Tags' 
        forum_tags_id = forum_tag.create({
            'name': 'Contract',
            'forum_id': forum_id.id,
        })

        # Post A user Questions
        usera_que_bef_karma = usera_record.karma
        usera_ques_id = forum_post.sudo(usera_id.id).create({
            'name': "Questions ?",
            'forum_id': forum_id.id,
            'tag_ids': [(4,forum_tags_id.id)],
        })
        usera_record.refresh()
        usera_que_aft_karma = usera_record.karma
        self.assertTrue((usera_que_aft_karma - usera_que_bef_karma) ==  forum_record.karma_gen_question_new, "Karma earned for new questions not match.")

        # Post A user Answer
        usera_ans_id = forum_post.sudo(usera_id.id).create({
            'forum_id': forum_id.id,
            'content': "Answers .",
            'parent_id': usera_ques_id.id,
        })

        # A upvote its question: not allowed
        usera_ques_create_uid = forum_post.sudo(usera_id.id).browse(usera_ques_id.id).create_uid.id
        self.assertTrue((usera_ques_create_uid == usera_id.id),"A upvote its question not allowed.")

        #A upvote its answer: not allowed
        usera_ques_create_uid = forum_post.sudo(usera_id.id).browse(usera_ans_id.id).create_uid.id
        self.assertTrue((usera_ques_create_uid == usera_id.id),"A upvote its answer not allowed.")

        #B comments A's question
        userb_id.write({'karma': forum_record.karma_comment_own})
        self.assertTrue((userb_record.karma >= forum_record.karma_comment_own) ,"User B karma is not enough comment A's question.")
        comment= "Comments ."
        comment_id = self.registry['forum.post'].message_post(cr, userb_id.id, usera_ques_id.id, comment, 'comment', subtype='mt_comment')

        #A converts the comment to an answer
        usera_id.write({'karma': forum_record.karma_comment_convert_all})
        self.assertTrue((usera_record.karma >= forum_record.karma_comment_convert_all) ,"A converts the comment to an answer is not enough karma")
        new_post_id = self.registry['forum.post'].convert_comment_to_answer(cr, usera_id.id, comment_id)

        #A converts its answer to a comment
        forum_post.convert_answer_to_comment(cr, usera_id.id, new_post_id)

        #Post B user Answer
        userb_ans_id = forum_post.sudo(userb_id.id).create({
            'forum_id': forum_id.id,
            'content': "Answers .",
            'parent_id': usera_ques_id.id,
        })

        # User A upvote B's User answer
        usera_id.write({'karma': forum_record.karma_gen_question_upvote})
        self.assertTrue((usera_record.karma >= forum_record.karma_upvote) ,"User A karma is not enough upvote answer.")
        usera_upv_bef_karma = usera_record.karma
        userb_upv_bef_karma = userb_record.karma

        self.registry['forum.post'].vote(cr, usera_id.id, [userb_ans_id.id], upvote=True)

        usera_record.refresh()
        userb_record.refresh()
        usera_upv_aft_karma = usera_record.karma
        userb_upv_aft_karma = userb_record.karma

        #check karma A user
        self.assertEqual(usera_upv_bef_karma, usera_upv_aft_karma, "karma update for a user is wrong.")
        #check karma B user
        self.assertTrue((userb_upv_aft_karma - userb_upv_bef_karma) ==  forum_record.karma_gen_answer_upvote, "karma gen answer upvote not match.")

        #Post A accepts B's answer
        usera_id.write({'karma': forum_record.karma_answer_accept_own})
        self.assertTrue((usera_record.karma >= forum_record.karma_answer_accept_own) ,"User A karma is not enough accept answer.")
        usera_accept_bef_karma = usera_record.karma
        userb_accept_bef_karma = userb_record.karma

        post = forum_post.sudo(usera_id.id).browse(userb_ans_id.id)
        self.registry['forum.post'].write(cr, usera_id.id, [post.id], {'is_correct': not post.is_correct})

        usera_record.refresh()
        userb_record.refresh()
        usera_accept_aft_karma = usera_record.karma
        userb_accept_aft_karma = userb_record.karma

        self.assertTrue((usera_accept_aft_karma - usera_accept_bef_karma) ==  forum_record.karma_gen_answer_accept, "karma gen answer accept not match.")
        self.assertTrue((userb_accept_aft_karma - userb_accept_bef_karma) ==  forum_record.karma_gen_answer_accepted, "karma gen answer accepted not match.")

        #User B down vote User A answer
        userb_id.write({'karma': forum_record.karma_downvote})
        self.assertTrue((userb_record.karma >= forum_record.karma_answer_accept_own) ,"User B karma is not enough accept answer.")
        usera_downv_bef_karma = usera_record.karma
        userb_downv_bef_karma = userb_record.karma

        self.registry['forum.post'].vote(cr, userb_id.id, [usera_ans_id.id], upvote=False)

        usera_record.refresh()
        userb_record.refresh()
        usera_downv_aft_karma = usera_record.karma
        userb_downv_aft_karma = userb_record.karma
        self.assertTrue((usera_downv_aft_karma - usera_downv_bef_karma) ==  forum_record.karma_gen_answer_downvote, "karma gen answer downvote not match.")
        self.assertEqual(userb_downv_bef_karma, userb_downv_aft_karma, "karma update for b user is wrong.")

        #A edits its own post
        usera_id.write({'karma': forum_record.karma_edit_own})
        self.assertTrue((usera_record.karma >= forum_record.karma_edit_own) ,"User A edit its own post karma is not enough.")
        vals={'content':"Edits ."}
        self.registry['forum.post'].write(cr, usera_id.id, [usera_ans_id.id], vals)

        # A edits B's post
        usera_id.write({'karma': forum_record.karma_edit_all})
        self.assertTrue((usera_record.karma >= forum_record.karma_edit_all) ,"User A edit B's post karma is not enough.")
        vals={'content': "Edits ."}
        self.registry['forum.post'].write(cr, usera_id.id, [userb_ans_id.id], vals)

        #A closes its own post
        usera_id.write({'karma': forum_record.karma_close_own})
        self.assertTrue((usera_record.karma >= forum_record.karma_close_own) ,"A closes its own post karma is not enough.")
        self.registry['forum.post'].close(cr, usera_id.id, [usera_ques_id.id], post_reason_id.id)

        #A closes B's post
        # Post B user Questions
        userb_ques_id = forum_post.sudo(userb_id.id).create({
            'name': "Question ?",
            'forum_id': forum_id.id,
            'tag_ids': [(4,forum_tags_id.id)],
        })

        usera_id.write({'karma': forum_record.karma_close_all})
        self.assertTrue((usera_record.karma >= forum_record.karma_close_all) ,"A closes b's post karma is not enough.")
        self.registry['forum.post'].close(cr, usera_id.id, [userb_ques_id.id], post_reason_id.id)

        #A delete its own post
        usera_id.write({'karma': forum_record.karma_unlink_own})
        self.assertTrue((usera_record.karma >= forum_record.karma_unlink_own) ,"A delete its own post karma is not enough.")
        self.registry['forum.post'].write(cr, usera_id.id, [usera_ques_id.id], {'active': False})

        #A delete B's post
        usera_id.write({'karma': forum_record.karma_unlink_all})
        self.assertTrue((usera_record.karma >= forum_record.karma_unlink_all) ,"A delete b's post karma is not enough.")
        self.registry['forum.post'].write(cr, usera_id.id, [userb_ques_id.id], {'active': False})
