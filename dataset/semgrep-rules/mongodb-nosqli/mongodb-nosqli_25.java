
package testcode.sqli;

import com.mongodb.BasicDBObject;
import com.mongodb.BasicDBObjectBuilder;

public class ContactsService {

  private MongoDatabase db = MongoClientUtil.mongoClient.getDatabase("test");
  private MongoCollection<Document> collection = db.getCollection("contacts");

  public ArrayList<Document> basicDBObjectBuilderStartKv(String userName, String email) {
    // ok: mongodb-nosqli
    BasicDBObject query = (BasicDBObject) BasicDBObjectBuilder
        .start("$where", "this.sharedWith == \"CONSTANT\" && this.email == \"CONSTANT\"")
        .get();

    MongoCursor<Document> cursor = collection.find(query).iterator();

    ArrayList<Document> results = new ArrayList<>();
    while (cursor.hasNext()) {
      Document doc = cursor.next();
      results.add(doc);
    }

    return results;
  }
}
