
package com.rands.couponproject.ejb;

import javax.jms.Message;

public class IncomeConsumerBean implements MessageListener{
    public void onMessage(Message msg) {
        // ruleid: insecure-jms-deserialization
        Object o = msg.getObject(); // variant 1 : calling getObject method directly on an ObjectMessage object
    }
}
