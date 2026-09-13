
package com.rands.couponproject.ejb;

import javax.jms.Message;
import com.rands.couponproject.jpa.Income;

public class IncomeConsumerBean implements MessageListener{
    public void onMessage(Message msg) {
        // ruleid: insecure-jms-deserialization
        Income income = (Income) msg.getObject(); // variant 2 : calling getObject method and casting to a custom class
    }
}
